"""Bridge chat turns to AIOS compose / approve / test / deploy flows."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.composer.credentials import secure_vault_save
from app.composer.deployment import deploy_solution_graph
from app.composer.planner import compile_solution_blueprint
from app.composer.recipes import is_express_recipe, progress_steps
from app.composer.workflow_composer import preview_graph_for_solution
from app.composer.chat_advanced import (
    boundary_event,
    clarify_event,
    heal_and_retest,
    is_complex_agent_goal,
    is_host_control_request,
    is_vague_goal,
    resolve_hitl,
    start_agent_os_plan,
)
from app.sandbox.enterprise_suite import run_enterprise_suite
from app.database import (
    Conversation,
    ConversationAttachment,
    KnowledgeBase,
    KnowledgeFile,
    WorkspaceIntegration,
)
from app.services import credential_vault as vault

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset(
    {
        "chat",
        "compose",
        "refine",
        "test",
        "deploy",
        "credential",
        "cancel",
        "approve",
        "agent_run",
        "hitl_approve",
        "hitl_reject",
        "heal",
        "run_workflow",
        "list_workflows",
        "workflow_status",
        "stop_run",
        "use_knowledge",
        "index_attachment",
        "list_credentials_needed",
        "capabilities",
        "monitor",
        "agent_execute",
    }
)


def _keyword_intent(text: str, *, has_pending: bool) -> str:
    t = (text or "").lower().strip()
    if not t:
        return "chat"

    if re.search(r"\b(cancel|abort|never\s*mind|nevermind)\b", t):
        return "cancel"

    if _extract_credential_updates(text) or looks_like_secret_message(text):
        return "credential"
    if re.search(r"\b(save|store|add)\b.*\b(credential|token|secret|api\s*key)\b", t):
        return "credential"
    if re.search(
        r"\b(already (gave|give|gives|added|provided|put|saved)|"
        r"in the credentials|credentials section|"
        r"i (already |also )?(gave|give|gives|added|put)|"
        r"all you need is in (the )?credentials)\b",
        t,
    ):
        return "credential"

    if re.search(r"\b(continue|hitl approve|approve hitl|resume agent)\b", t):
        return "hitl_approve"
    if re.search(r"\b(hitl reject|reject hitl|reject agent)\b", t):
        return "hitl_reject"

    if re.search(r"\b(heal|fix (the )?graph|repair)\b", t):
        return "heal"

    if re.search(r"\bwhat can you do\b|\bcapabilities\b", t):
        return "capabilities"
    if re.search(r"\blist (my )?workflows\b|\bshow (my )?workflows\b", t):
        return "list_workflows"
    if re.search(r"\b(status of|workflow status|last run|run status|monitor)\b", t):
        return "workflow_status"
    if re.search(r"\bstop (this |the )?(run|workflow)\b", t):
        return "stop_run"
    if re.search(r"\b(run|execute)\b.*\bworkflow\b|\brun (my )?(last )?workflow\b|\brun workflow\b|\bnow can you run\b|\bexecute workflow\b|\brun the workflow\b", t):
        return "run_workflow"
    if re.search(r"\b(build|create|make|compose|generate)\b.*\b(workflow|bot|automation|agent|email|digest|system)\b|\bbuild a workflow\b|\bmake a workflow\b|\bworkflow for this\b|\bbuild a workflow for this\b", t):
        return "compose"
    if re.search(r"\bsend\b.*\b(emails?|mail)\b|\b(emails?|mail)\b.*\b(send|sending)\b|\bwant\s+to\s+send\b", t):
        return "compose"
    if re.search(r"\bindex (my )?attachments?\b|\bindex (these|the) files?\b", t):
        return "index_attachment"
    if re.search(r"\buse knowledge\b|\buse (the )?knowledge base\b", t):
        return "use_knowledge"
    if re.search(r"\b(list )?missing credentials\b|\bwhat credentials\b", t):
        return "list_credentials_needed"

    if re.search(
        r"\b(approve|confirm|looks good|lgtm|go ahead|yes,? approve|accept (the )?plan|make it|can you make it|now run it|run it|do it|direct access|direct acess)\b",
        t,
    ):
        return "approve"

    if t.startswith("deploy") or "deploy this" in t or "publish this" in t or t == "publish":
        return "deploy"

    if re.search(r"\b(run test|test (this|it|the (plan|workflow|solution))|sandbox|trial run|retest|test workflow)\b", t) or t in (
        "test",
        "run test",
        "retest",
    ):
        return "test"

    if re.search(r"\b(express compose|compose faster|fast compose|quick compose)\b", t):
        return "compose"

    if has_pending and re.search(r"\b(refine|update plan|change (the )?plan|add (a )?node|tweak)\b", t):
        return "refine"

    if is_complex_agent_goal(t) or re.search(r"\b(run agent|agent plan|agent os)\b", t):
        return "agent_run"

    compose_patterns = (
        "create workflow",
        "build workflow",
        "compose workflow",
        "build a workflow for this",
        "build agent",
        "create agent",
        "aios",
        "automation",
        "automate this",
        "build a bot",
        "create a bot",
        "ordering system",
        "telegram bot",
        "support bot",
        "build a telegram",
        "create a telegram",
        "email digest",
        "github issue",
        "webhook",
        "onboard new hires",
        "invoice reminder",
        "welcome email",
        "status report",
        "lead capture",
        "send email",
        "send emails",
    )
    if re.search(r"\b(build|create|make|compose|generate)\b.*\b(workflow|bot|automation|agent|email|digest|system)\b|\bbuild a workflow\b|\bmake a workflow\b|\bworkflow for this\b|\bbuild a workflow for this\b", t):
        return "compose"
    if re.search(r"\bsend\b.*\b(emails?|mail)\b|\b(emails?|mail)\b.*\b(send|sending)\b|\bwant\s+to\s+send\b", t):
        return "compose"
    if any(p in t for p in compose_patterns):
        return "compose"
    if ("i want" in t or "i need" in t or t.startswith("build ") or t.startswith("create ")) and any(
        k in t for k in ("workflow", "bot", "automation", "agent", "system", "digest", "github", "email")
    ):
        return "compose"

    if has_pending and re.search(r"\b(refine|update|change|add)\b", t) and any(
        k in t for k in ("plan", "workflow", "node", "agent", "bot")
    ):
        return "refine"

    return "chat"


def _llm_classify_intent(text: str, *, has_pending: bool, db: Session | None = None, user_id: int | None = None) -> str | None:
    """Best-effort LLM intent classify using user-specific or system provider configuration."""
    from app.services.llm_providers import get_active_config
    try:
        cfg = get_active_config(db, user_id=user_id)
        api_key = cfg.get("api_key", "").strip()
        base = cfg.get("base_url", "").rstrip("/")
        model = cfg.get("model", "") or "gpt-4o-mini"
    except Exception:
        api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()
        base = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("NOVAFLOW_INTENT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    if not api_key or len(text) < 4:
        return None
    prompt = (
        "Classify the user chat message into exactly one intent label.\n"
        "Labels: chat, compose, refine, test, deploy, credential, cancel, approve, "
        "agent_run, hitl_approve, hitl_reject, heal, run_workflow, list_workflows, "
        "workflow_status, use_knowledge, index_attachment, capabilities, monitor\n"
        f"Pending AIOS plan exists: {bool(has_pending)}\n"
        "compose = build/create a workflow/bot/automation\n"
        "agent_run = multi-agent / research / complex planning\n"
        "approve = confirm the proposed plan\n"
        "test = sandbox/trial run\n"
        "deploy = publish workflow\n"
        "heal = repair failed graph\n"
        "credential = providing API keys/tokens\n"
        "Reply with ONLY the label.\n\n"
        f"Message: {text[:800]}"
    )
    try:
        import httpx

        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 8,
            },
            timeout=4.0,
        )
        if resp.status_code >= 400:
            return None
        content = (
            (((resp.json() or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        )
        label = content.strip().lower().split()[0] if content.strip() else ""
        label = label.strip(".,:;\"'`")
        if label in VALID_INTENTS:
            return label
    except Exception as exc:  # noqa: BLE001
        logger.debug("intent LLM classify skipped: %s", exc)
    return None


def classify_intent(text: str, *, has_pending: bool = False, db: Session | None = None, user_id: int | None = None) -> str:
    """LLM intent with keyword fallback."""
    llm = _llm_classify_intent(text, has_pending=has_pending, db=db, user_id=user_id)
    if llm:
        return llm
    return _keyword_intent(text, has_pending=has_pending)


_CRED_MAP = {
    "telegram_bot_token": ("telegram", "telegram_bot", "bot_token"),
    "github_token": ("github", "github_pat", "token"),
    "slack_webhook_url": ("slack", "slack_webhook", "webhook_url"),
    "slack_bot_token": ("slack", "slack_bot", "bot_token"),
    "discord_webhook_url": ("discord", "discord_webhook", "webhook_url"),
    "smtp_password": ("email", "gmail_smtp", "smtp_password"),
    "smtp_user": ("email", "gmail_smtp", "smtp_user"),
    "smtp_host": ("email", "gmail_smtp", "smtp_host"),
    "smtp_from": ("email", "gmail_smtp", "smtp_from"),
    "jira_api_token": ("jira", "jira_cloud", "api_key"),
    "linear_api_key": ("linear", "linear_api", "api_key"),
    "openai_api_key": ("llm", "openai", "api_key"),
    "api_key": ("llm", "openai", "api_key"),
}

_GMAIL_APP_PASSWORD = re.compile(r"\b([a-z]{4}(?:\s+[a-z]{4}){3})\b", re.I)
_LLM_API_KEY = re.compile(r"\b(sk-or-v1-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})\b")
_EMAIL_ADDR = re.compile(r"\b([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\b", re.I)

# Event types that should not become their own chat cards when a stronger card exists
_SECONDARY_UI_TYPES = frozenset(
    {
        "aios_memory",
        "aios_requirements",
        "aios_fulfillment",
        "aios_progress",
        "aios_suggest",
    }
)

_PRIMARY_PRIORITY = (
    "aios_credentials_saved",
    "aios_credentials_needed",
    "aios_deploy",
    "aios_test_report",
    "aios_sandbox",
    "aios_approved",
    "aios_heal",
    "aios_hitl",
    "aios_solution",
    "aios_clarify",
    "aios_cancelled",
    "aios_denied",
    "aios_progress",
)


def looks_like_secret_message(text: str) -> bool:
    """True when the message looks like pasted secrets (never send to demo RAG)."""
    from app.composer.chat_channels import looks_like_channel_secret

    t = (text or "").strip()
    if not t:
        return False
    if looks_like_channel_secret(t):
        return True
    if _LLM_API_KEY.search(t):
        return True
    if _GMAIL_APP_PASSWORD.search(t) and re.search(
        r"\b(pass|password|smtp|gmail|email|app\s*password|credential)\b", t, re.I
    ):
        return True
    if re.fullmatch(r"\s*" + _GMAIL_APP_PASSWORD.pattern + r"\s*", t, flags=re.I):
        return True
    if re.search(r"\b(my\s+)?(email|gmail)\s+is\b", t, re.I) and (
        _EMAIL_ADDR.search(t) or _GMAIL_APP_PASSWORD.search(t)
    ):
        return True
    return False


def _extract_credential_updates(text: str) -> list[dict[str, Any]]:
    """Merge channel-registry NL extract with legacy labeled key:=value forms."""
    from app.composer.chat_channels import extract_channel_credentials

    found = extract_channel_credentials(text)
    # Also keep legacy labeled patterns that registry may miss
    t = (text or "").strip()
    if not t:
        return found

    bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in found:
        key = (item["category"], item["kind"], item.get("label") or "default")
        bucket[key] = item

    def ensure(cat: str, kind: str) -> dict[str, Any]:
        return bucket.setdefault(
            (cat, kind, "default"),
            {"category": cat, "kind": kind, "label": "default", "fields": {}, "raw_secrets": []},
        )

    patterns = [
        (r"(telegram_bot_token|telegram token)\s*[:=]\s*([^\s]+)", "telegram", "telegram_bot", "bot_token"),
        (r"(github_token|github token|github pat)\s*[:=]\s*([^\s]+)", "github", "github_pat", "token"),
        (r"(slack_webhook_url|slack webhook)\s*[:=]\s*(https?://\S+)", "slack", "slack_webhook", "webhook_url"),
        (r"(discord_webhook_url|discord webhook)\s*[:=]\s*(https?://\S+)", "discord", "discord_webhook", "webhook_url"),
        (
            r"(smtp_password|email password|app password)\s*[:=]\s*([a-z]{4}(?:\s+[a-z]{4}){3}|[^\s]+)",
            "email",
            "gmail_smtp",
            "smtp_password",
        ),
        (r"(jira_api_token|jira token)\s*[:=]\s*([^\s]+)", "jira", "jira_cloud", "api_key"),
        (r"(linear_api_key|linear key)\s*[:=]\s*([^\s]+)", "linear", "linear_api", "api_key"),
        (
            r"(openai_api_key|openrouter_api_key|llm api key)\s*[:=]\s*([^\s]+)",
            "llm",
            "openai",
            "api_key",
        ),
        # Add pattern for "my llm api key is" or "i have llm api key"
        (
            r"(my llm api key is|i have llm api key|api key is)\s*([^\s]+)",
            "llm",
            "openai",
            "api_key",
        ),
    ]
    for pat, cat, kind, field in patterns:
        m = re.search(pat, t, flags=re.I)
        if not m:
            continue
        val = m.group(2).strip().strip("\"'")
        if field == "smtp_password":
            val = re.sub(r"\s+", "", val)
        slot = ensure(cat, kind)
        slot["fields"][field] = val
        slot.setdefault("raw_secrets", []).append(m.group(2).strip())

    return list(bucket.values())

def redact_secrets_in_text(text: str, secrets: list[str] | None = None) -> str:
    out = text or ""
    for s in secrets or []:
        if s and len(s) >= 6 and s in out:
            out = out.replace(s, "***REDACTED***")
    out = re.sub(r"(https://hooks\.slack\.com/\S+)", "***REDACTED***", out, flags=re.I)
    out = re.sub(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b", "***REDACTED***", out)
    out = re.sub(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b", "***REDACTED***", out)
    out = re.sub(r"\bsk-[A-Za-z0-9_-]{20,}\b", "***REDACTED***", out)
    out = re.sub(r"\b([a-z]{4}(?:\s+[a-z]{4}){3})\b", "***REDACTED***", out, flags=re.I)
    return out


def _select_primary_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not events:
        return None
    by_type = {e.get("type"): e for e in events if isinstance(e, dict) and e.get("type")}
    for t in _PRIMARY_PRIORITY:
        if t in by_type:
            return by_type[t]
    for e in events:
        if isinstance(e, dict) and e.get("type") and e.get("type") not in _SECONDARY_UI_TYPES:
            return e
    return events[0] if events else None


def _ui_events_from(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = _select_primary_event(events)
    if not primary:
        return []
    return [primary]


def apply_workspace_credentials(
    db: Session,
    workspace_id: int,
    updates: dict[str, str] | list[dict[str, Any]],
    *,
    user_id: int = 0,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    raw_secrets: list[str] = []

    if isinstance(updates, dict):
        items: list[dict[str, Any]] = []
        for k, v in updates.items():
            mapped = _CRED_MAP.get(k)
            if not mapped or not v:
                continue
            cat, kind, field = mapped
            items.append(
                {
                    "category": cat,
                    "kind": kind,
                    "label": "default",
                    "fields": {field: v},
                    "raw_secrets": [v],
                }
            )
    else:
        items = updates

    for item in items:
        fields = item.get("fields") or {}
        if not fields:
            continue
        raw_secrets.extend(item.get("raw_secrets") or [str(v) for v in fields.values()])
        row = vault.upsert_from_chat(
            db,
            workspace_id=workspace_id,
            user_id=user_id or 0,
            category=item["category"],
            kind=item["kind"],
            label=item.get("label") or "default",
            fields=fields,
        )
        saved.append({"id": row.id, "category": row.category, "kind": row.kind, "label": row.label})
        if (item.get("label") or "default") == "default":
            flat = {}
            if item["category"] == "telegram" and fields.get("bot_token"):
                flat["telegram_bot_token"] = fields["bot_token"]
            if item["category"] == "github" and fields.get("token"):
                flat["github_token"] = fields["token"]
            if item["category"] == "slack" and fields.get("webhook_url"):
                flat["slack_webhook_url"] = fields["webhook_url"]
            if flat:
                _legacy_apply(db, workspace_id, flat)
            # Always sync email defaults into legacy for gap fallback
            if item["category"] == "email" and (item.get("label") or "default") == "default":
                email_flat = {}
                if fields.get("smtp_password"):
                    email_flat["smtp_password"] = fields["smtp_password"]
                if fields.get("smtp_user"):
                    email_flat["smtp_user"] = fields["smtp_user"]
                if fields.get("smtp_host"):
                    email_flat["smtp_host"] = fields["smtp_host"]
                if fields.get("smtp_from"):
                    email_flat["smtp_from"] = fields["smtp_from"]
                if email_flat:
                    _legacy_apply_email(db, workspace_id, email_flat)

    return {
        "updated": [f"{s['label']}:{s['category']}" for s in saved],
        "entries": saved,
        "raw_secrets": raw_secrets,
    }


def _legacy_apply_email(db: Session, workspace_id: int, updates: dict[str, str]) -> None:
    row = db.query(WorkspaceIntegration).filter(WorkspaceIntegration.workspace_id == workspace_id).first()
    if not row:
        row = WorkspaceIntegration(workspace_id=workspace_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    if updates.get("smtp_password"):
        row.smtp_password_enc = secure_vault_save(updates["smtp_password"])
    if updates.get("smtp_user"):
        row.smtp_user = str(updates["smtp_user"])[:255]
    if updates.get("smtp_host"):
        row.smtp_host = str(updates["smtp_host"])[:255]
    if updates.get("smtp_from"):
        row.smtp_from = str(updates["smtp_from"])[:255]
    db.commit()


def _legacy_apply(db: Session, workspace_id: int, updates: dict[str, str]) -> None:
    row = db.query(WorkspaceIntegration).filter(WorkspaceIntegration.workspace_id == workspace_id).first()
    if not row:
        row = WorkspaceIntegration(workspace_id=workspace_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    if updates.get("telegram_bot_token"):
        row.telegram_bot_token_enc = secure_vault_save(updates["telegram_bot_token"])
    if updates.get("github_token"):
        row.github_token_enc = secure_vault_save(updates["github_token"])
    if updates.get("slack_webhook_url"):
        row.slack_webhook_url_enc = secure_vault_save(updates["slack_webhook_url"])
    db.commit()


def _load_conv_meta(db: Session, conversation_id: str) -> tuple[Conversation | None, dict[str, Any]]:
    conv = db.get(Conversation, conversation_id) if conversation_id else None
    if not conv:
        return None, {}
    try:
        meta = json.loads(conv.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return conv, meta


def _save_conv_meta(db: Session, conv: Conversation | None, meta: dict[str, Any]) -> None:
    if not conv:
        return
    conv.meta_json = json.dumps(meta)
    db.commit()


def _attachment_knowledge_id(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
) -> int | None:
    if not conversation_id:
        return None
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.conversation_id == conversation_id,
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.deleted_at.is_(None),
        )
        .all()
    )
    if not rows:
        return None
    existing_kb_id = None
    try:
        conv = db.get(Conversation, conversation_id)
        if conv and conv.meta_json:
            conv_meta = json.loads(conv.meta_json or "{}")
            existing_kb_id = (conv_meta.get("aios") or {}).get("knowledge_id")
    except Exception:
        existing_kb_id = None
    if existing_kb_id:
        kb = db.get(KnowledgeBase, int(existing_kb_id))
        if kb and kb.workspace_id == workspace_id:
            return kb.id
    kb = KnowledgeBase(
        name=f"Chat Attachments {str(conversation_id)[:8]}",
        description="Auto-indexed from chat conversation attachments.",
        user_id=user_id,
        workspace_id=workspace_id,
        type=0,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    file_records: list[KnowledgeFile] = []
    for r in rows[:8]:
        file_records.append(
            KnowledgeFile(
                knowledge_id=kb.id,
                file_name=r.file_name or "attachment",
                file_path=r.storage_key or "",
                status=5,
            )
        )
    db.add_all(file_records)
    db.commit()
    try:
        import threading

        from app.services.knowledge import process_file_records_bg

        threading.Thread(
            target=process_file_records_bg,
            args=([fr.id for fr in file_records], 1000, 100),
            daemon=True,
        ).start()
    except Exception as exc:  # noqa: BLE001
        logger.warning("bg attachment index failed: %s", exc)
        from app.services.knowledge import process_file_record

        for fr in file_records:
            try:
                process_file_record(db, fr, chunk_size=1000, chunk_overlap=100)
            except Exception:  # noqa: BLE001
                pass
    return kb.id


def _run_sandbox_for_aios(
    db: Session,
    aios: dict[str, Any],
    *,
    workspace_id: int | None = None,
) -> dict[str, Any]:
    solution_id = aios.get("solution_id")
    preview = aios.get("executable_preview") or {}
    if solution_id and not (preview.get("nodes") if isinstance(preview, dict) else None):
        try:
            preview = preview_graph_for_solution(db, solution_id, knowledge_id=aios.get("knowledge_id"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("preview_graph_for_solution failed: %s", exc)
            preview = aios.get("graph") or {}
    report = run_enterprise_suite(
        preview if isinstance(preview, dict) else {},
        missing_credentials=aios.get("missing_credentials") or [],
        field=aios.get("last_field") or (aios.get("recipe") or {}).get("field"),
        db=db,
        workspace_id=workspace_id or aios.get("workspace_id"),
        live_credential_probe=True,
    )
    report["solution_id"] = solution_id
    report["node_types"] = aios.get("node_types") or (preview.get("meta") or {}).get("node_types") or []
    return report


def _emit_progress(aios: dict[str, Any]) -> dict[str, Any]:
    mode = "agent" if (aios.get("agent_os") or {}).get("mode") == "agent" else "workflow"
    data: dict[str, Any] = {
        "steps": aios.get("progress")
        or progress_steps(missing_credentials=aios.get("missing_credentials"), mode=mode),
        "status": aios.get("status"),
        "next_action": aios.get("next_action") or "approve",
        "recipe_name": aios.get("recipe_name"),
    }
    if aios.get("compose_ms") is not None:
        data["compose_ms"] = aios.get("compose_ms")
    if aios.get("express"):
        data["express"] = True
    if aios.get("knowledge_id"):
        data["knowledge_id"] = aios.get("knowledge_id")
    if aios.get("attachment_count") is not None:
        data["attachment_count"] = aios.get("attachment_count")
    return {"type": "aios_progress", "data": data}


def _attachment_count(db: Session, conversation_id: str | None, workspace_id: int) -> int:
    if not conversation_id:
        return 0
    return (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.conversation_id == conversation_id,
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.deleted_at.is_(None),
        )
        .count()
    )


def _wants_express(text: str, goal: str) -> bool:
    t = (text or "").lower()
    if re.search(r"\b(express compose|compose faster|fast compose|quick compose)\b", t):
        return True
    return is_express_recipe(goal) and not is_vague_goal(goal) and not is_complex_agent_goal(goal)


def _build_cred_chips(
    required_caps: list[str],
    missing: list[str],
    missing_slots: list[dict],
) -> list[str]:
    from app.composer.chat_channels import paste_hints_for_missing

    cred_chips: list[str] = []
    if missing:
        hints = paste_hints_for_missing(missing)
        cred_chips = (hints[:1] if hints else [])
        if "cap_google" in required_caps:
            cred_chips.append("Use Google OAuth")
        if "cap_smtp" in required_caps:
            cred_chips.append("Use SMTP")
        cred_chips.append("Open Credentials")
    if not missing_slots and not missing:
        return ["Approve"]
    if not missing:
        return ["Approve"]
    return cred_chips


def _refresh_blueprint_from_aios(
    db: Session,
    *,
    workspace_id: int,
    conv,
    meta: dict[str, Any],
    aios: dict[str, Any],
) -> dict[str, Any]:
    """Recompute gaps and return an updated aios_solution card payload."""
    from app.composer.gap_analysis import analyze_solution_gaps, credential_slots_for_missing
    from app.composer.planner import infer_capabilities_from_goal
    from app.composer.workflow_composer import build_executable_graph
    from app.composer.recipes import match_recipe
    from app.composer.chat_requirements import (
        build_blueprint_preview,
        compose_goal_from_requirements,
        gather_prompt,
        missing_workflow_slots,
        sync_checklist_from_aios,
    )
    from app.composer.chat_channels import friendly_title_for_goal

    req = dict(aios.get("requirements") or {})
    enriched_goal = compose_goal_from_requirements(req)
    required_caps = list(
        aios.get("required_capabilities")
        or infer_capabilities_from_goal(enriched_goal, force_workflow=True)
    )
    live_missing = analyze_solution_gaps(db, workspace_id, required_caps)
    missing_slots = missing_workflow_slots(req)
    compose_phase = "gather" if missing_slots or live_missing else "await_approve"
    next_action = "gather" if missing_slots else ("credentials" if live_missing else "approve")
    recipe_goal = req.get("raw") or req.get("goal") or enriched_goal
    if req.get("integration"):
        recipe_goal = f"{req.get('integration')} {recipe_goal}"
    recipe = match_recipe(recipe_goal, fallback_generic=True)
    recipe_name = (recipe or {}).get("name")
    preview_executable = build_executable_graph(
        required_caps=required_caps,
        goal=enriched_goal,
        knowledge_id=aios.get("knowledge_id"),
        recipe_id=(recipe or {}).get("id"),
        requirements=req,
        db=db,
        workspace_id=workspace_id,
    )
    blueprint = build_blueprint_preview(
        enriched_goal, req, required_caps, preview_executable, missing_credentials=live_missing
    )
    friendly_title = req.get("workflow_name") or aios.get("friendly_title") or friendly_title_for_goal(enriched_goal)

    aios.update(
        {
            "goal": enriched_goal,
            "missing_credentials": live_missing,
            "compose_phase": compose_phase,
            "phase": "blueprint",
            "status": "blueprint",
            "next_action": next_action,
            "required_capabilities": required_caps,
            "executable_preview": preview_executable,
            "blueprint": blueprint,
            "credential_slots": credential_slots_for_missing(live_missing),
            "friendly_title": friendly_title,
            "recipe_name": recipe_name,
            "progress": progress_steps(missing_credentials=live_missing),
        }
    )
    aios["requirements"] = sync_checklist_from_aios(dict(req), aios)
    meta["aios"] = aios
    _save_conv_meta(db, conv, meta)

    missing = live_missing
    cred_chips = _build_cred_chips(required_caps, missing, missing_slots)
    blueprint = aios.get("blueprint") or {}
    preview_nodes = blueprint.get("preview_nodes") or preview_executable.get("nodes") or []
    preview_edges = blueprint.get("preview_edges") or preview_executable.get("edges") or []

    return {
        **aios,
        "friendly_title": friendly_title,
        "display_recipe": (
            None if recipe_name and "generic" in str(recipe_name).lower() else recipe_name
        ),
        "nodes": preview_nodes,
        "edges": preview_edges,
        "test_report": None,
        "credentials_url": "/credentials",
        "chips": cred_chips,
        "message": gather_prompt(req, missing_slots, missing),
    }


def process_chat_goal(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
) -> dict[str, Any]:
    text = (user_message or "").strip()
    conv, meta = _load_conv_meta(db, conversation_id or "")
    events: list[dict[str, Any]] = []
    blocked_normal_reply = False
    redacted_message = text
    aios = meta.get("aios") if isinstance(meta.get("aios"), dict) else {}
    has_pending = bool(
        aios.get("solution_id")
        or aios.get("compose_phase") in ("gather", "await_approve", "blueprint")
        or aios.get("phase") == "blueprint"
        or (aios.get("agent_os") or {}).get("plan_session_id")
    ) and aios.get("status") not in ("deployed", "cancelled", "done")

    if is_host_control_request(text):
        events.append(boundary_event())
        return _finalize(events, True, redacted_message)

    # Universal router: ops | work | agent | qa | pending | boundary
    from app.composer.chat_actions import OPS_INTENTS, classify_ops_intent
    from app.composer.chat_router import infer_field, universal_route

    route_info = universal_route(
        text,
        has_pending=has_pending,
        last_field=aios.get("last_field"),
    )

    if route_info.get("route") == "ops" or (
        route_info.get("ops_intent") and route_info.get("ops_intent") in OPS_INTENTS
    ):
        ops_intent = route_info.get("ops_intent") or classify_ops_intent(text)
        return {
            "events": [],
            "blocked_normal_reply": True,
            "summary": "",
            "redacted_message": redacted_message,
            "ops_intent": ops_intent,
            "needs_ops_dispatch": True,
        }

    if route_info.get("route") == "boundary":
        events.append(boundary_event())
        return _finalize(events, True, redacted_message)

    intent = route_info.get("intent_hint") or classify_intent(text, has_pending=has_pending)
    if intent == "chat" and aios.get("compose_phase") in ("gather", "await_approve", "blueprint"):
        intent = "refine"
    if route_info.get("route") == "work_compose":
        intent = "compose" if intent not in ("refine",) else intent
    if route_info.get("route") == "agent" or (intent == "compose" and is_complex_agent_goal(text)):
        intent = "agent_run"

    # Legacy ops check (belt-and-suspenders)
    ops_intent = classify_ops_intent(text)
    if ops_intent and ops_intent in OPS_INTENTS and route_info.get("route") != "work_compose":
        return {
            "events": [],
            "blocked_normal_reply": True,
            "summary": "",
            "redacted_message": redacted_message,
            "ops_intent": ops_intent,
            "needs_ops_dispatch": True,
        }

    # Credentials can ride along with other intents — never fall through to demo RAG
    credential_items = _extract_credential_updates(text)
    if (
        not credential_items
        and looks_like_secret_message(text)
        and (
            any("smtp" in str(m).lower() for m in (aios.get("missing_credentials") or []))
            or aios.get("solution_id")
        )
    ):
        bare = re.fullmatch(r"\s*([a-z]{4}(?:\s+[a-z]{4}){3})\s*", text.strip(), flags=re.I)
        if bare:
            credential_items = [
                {
                    "category": "email",
                    "kind": "gmail_smtp",
                    "label": "default",
                    "fields": {"smtp_password": re.sub(r"\s+", "", bare.group(1))},
                    "raw_secrets": [bare.group(1)],
                }
            ]
    if credential_items or intent == "credential" or (
        looks_like_secret_message(text) and intent not in ("compose", "refine", "agent_run")
    ):
        if credential_items:
            from app.composer.gap_analysis import analyze_solution_gaps

            cred_res = apply_workspace_credentials(db, workspace_id, credential_items, user_id=user_id)
            redacted_message = redact_secrets_in_text(text, cred_res.get("raw_secrets") or [])
            blocked_normal_reply = True
            
            # Check if LLM API key was provided and store it for conversation use
            for item in credential_items:
                if item.get("category") == "llm" and item.get("kind") == "openai":
                    api_key = item.get("fields", {}).get("api_key")
                    if api_key:
                        # Store API key in conversation context for immediate use
                        aios["conversation_api_key"] = api_key
                        # Also save to vault for persistent use
                        try:
                            from app.services import credential_vault as vault

                            vault.upsert_from_chat(
                                db,
                                workspace_id=workspace_id,
                                user_id=user_id,
                                category="llm",
                                kind="openai",
                                label="Conversation-provided API key",
                                fields={"api_key": api_key},
                            )
                        except Exception as e:
                            logger.warning("Failed to save API key to vault: %s", e)
            
            caps = aios.get("required_capabilities") or []
            missing: list[str] = []
            if caps:
                missing = analyze_solution_gaps(db, workspace_id, caps)
                aios["missing_credentials"] = missing
                if aios.get("approved"):
                    aios["next_action"] = "test" if not missing else "credentials"
                else:
                    aios["next_action"] = "approve" if not missing else "credentials"
                meta["aios"] = aios
                _save_conv_meta(db, conv, meta)
            from app.composer.chat_requirements import missing_workflow_slots

            missing_slots = missing_workflow_slots(dict(aios.get("requirements") or {}))
            chips = _build_cred_chips(caps, missing, missing_slots)
            if not missing and aios.get("solution_id"):
                msg = (
                    "Saved your login in Credentials. Next: tap **Approve**, then I’ll run the test."
                    if not aios.get("approved")
                    else "Saved your login in Credentials. Next: tap **Run test**."
                )
            elif not missing:
                msg = "Saved your credentials in the vault. Ask me to build or continue your automation."
            else:
                still = ", ".join(str(m).replace("_", " ") for m in missing[:4])
                msg = f"Saved what you sent. Still need: {still}. Paste them here or open Credentials."
            events.append(
                {
                    "type": "aios_credentials_saved",
                    "data": {
                        **cred_res,
                        "message": msg,
                        "chips": chips,
                        "missing": missing,
                        "next_action": aios.get("next_action") or ("approve" if not missing else "credentials"),
                    },
                }
            )
            if (
                caps
                and (
                    aios.get("compose_phase") in ("gather", "await_approve", "blueprint")
                    or aios.get("phase") == "blueprint"
                )
            ):
                solution_card = _refresh_blueprint_from_aios(
                    db,
                    workspace_id=workspace_id,
                    conv=conv,
                    meta=meta,
                    aios=aios,
                )
                events.append({"type": "aios_solution", "data": solution_card})
            # One card only — do not also emit credentials_needed / progress
        elif intent == "credential" or looks_like_secret_message(text):
            from app.composer.gap_analysis import analyze_solution_gaps
            from app.composer.chat_channels import friendly_missing_name, paste_hints_for_missing

            caps = aios.get("required_capabilities") or []
            # Also treat "already in credentials" as a vault re-check
            check_caps = caps if caps else (["cap_smtp"] if aios.get("solution_id") else [])
            missing = (
                analyze_solution_gaps(db, workspace_id, check_caps)
                if check_caps
                else list(aios.get("missing_credentials") or [])
            )
            aios["missing_credentials"] = missing
            if not missing and aios.get("solution_id"):
                aios["next_action"] = "approve" if not aios.get("approved") else "test"
                meta["aios"] = aios
                _save_conv_meta(db, conv, meta)
                events.append(
                    {
                        "type": "aios_credentials_saved",
                        "data": {
                            "message": (
                                "Login found in Credentials — tap **Approve** to continue."
                                if not aios.get("approved")
                                else "Credentials look good — tap **Run test**."
                            ),
                            "chips": ["Approve", "Run test"] if not aios.get("approved") else ["Run test", "Deploy"],
                            "missing": [],
                            "updated": [],
                        },
                    }
                )
                blocked_normal_reply = True
                redacted_message = redact_secrets_in_text(text)
            else:
                meta["aios"] = aios
                _save_conv_meta(db, conv, meta)
                names = ", ".join(friendly_missing_name(m) for m in (missing or [])[:4])
                hints = paste_hints_for_missing(missing or [])
                events.append(
                    {
                        "type": "aios_credentials_needed",
                        "data": {
                            "missing": missing
                            or hints
                            or [
                                "Paste credentials here, or open Credentials and save them."
                            ],
                            "credentials_url": "/credentials",
                            "message": (
                                f"I couldn’t find the login in Credentials yet"
                                + (f" (need: {names})" if names else "")
                                + ". Paste them here, or open Credentials and save."
                            ),
                            "chips": (hints[:1] if hints else []) + ["Open Credentials"],
                        },
                    }
                )
                blocked_normal_reply = True
                redacted_message = redact_secrets_in_text(text)
        if intent == "credential" or credential_items or looks_like_secret_message(text):
            return _finalize(events, blocked_normal_reply, redacted_message, goal=aios.get("goal") or "")

    agent_os = aios.get("agent_os") if isinstance(aios.get("agent_os"), dict) else {}

    if intent in ("hitl_approve", "hitl_reject") or (
        intent == "approve" and agent_os.get("hitl", {}).get("status") == "pending"
    ):
        run_id = agent_os.get("run_id")
        if not run_id:
            events.append({"type": "aios_hitl", "data": {"status": "error", "message": "No pending HITL request."}})
            return _finalize(events, True, redacted_message)
        approved = intent != "hitl_reject"
        hitl = resolve_hitl(db, run_id=run_id, approved=approved)
        agent_os["hitl"] = hitl
        agent_os["status"] = "approved" if approved else "rejected"
        aios["agent_os"] = agent_os
        aios["status"] = agent_os["status"]
        aios["next_action"] = "deploy" if approved and aios.get("solution_id") else ("done" if approved else "cancel")
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        events.append({"type": "aios_hitl", "data": {**hitl, "run_id": run_id}})
        events.append(_emit_progress(aios))
        out = _finalize(events, True, redacted_message)
        if approved and aios.get("mode") == "agent":
            out["pending_agent_execute"] = True
            out["agent_goal"] = aios.get("goal") or text
            out["agent_knowledge_id"] = aios.get("knowledge_id")
            out["agent_os"] = agent_os
        return out

    if intent == "cancel" and has_pending:
        aios["status"] = "cancelled"
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        events.append({"type": "aios_cancelled", "data": {"solution_id": aios.get("solution_id")}})
        return _finalize(events, True, redacted_message)

    if intent == "heal" or (intent == "test" and aios.get("status") == "test_failed"):
        if not aios.get("executable_preview") and not aios.get("solution_id"):
            events.append({"type": "aios_heal", "data": {"status": "error", "message": "Nothing to heal yet."}})
            return _finalize(events, True, redacted_message)
        heal_count = int(aios.get("heal_count") or 0)
        if heal_count >= 1 and intent == "heal" and not re.search(r"\bheal again\b|\bforce heal\b", text, re.I):
            events.append(
                {
                    "type": "aios_heal",
                    "data": {
                        "status": "ask",
                        "message": "Already auto-healed once. Say **heal again** to retry, or refine the plan.",
                        "fixes": [],
                    },
                }
            )
            return _finalize(events, True, redacted_message)
        preview = aios.get("executable_preview") or {}
        if aios.get("solution_id") and not preview.get("nodes"):
            try:
                preview = preview_graph_for_solution(db, aios["solution_id"], knowledge_id=aios.get("knowledge_id"))
            except Exception:  # noqa: BLE001
                preview = aios.get("graph") or {}
        healed, report, fixes = heal_and_retest(
            preview,
            knowledge_id=aios.get("knowledge_id"),
            missing_credentials=aios.get("missing_credentials") or [],
        )
        aios["executable_preview"] = healed
        aios["node_types"] = (healed.get("meta") or {}).get("node_types") or aios.get("node_types")
        aios["last_test"] = report
        aios["tested"] = report.get("status") == "success"
        aios["status"] = "tested" if aios["tested"] else "test_failed"
        aios["next_action"] = "deploy" if aios["tested"] else "heal"
        aios["heal_count"] = heal_count + 1
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        events.append({"type": "aios_heal", "data": {"fixes": fixes, "status": "ok", "heal_count": aios["heal_count"]}})
        events.append({"type": "aios_test_report", "data": report})
        events.append(
            {
                "type": "aios_run_status",
                "data": {
                    "status": report.get("status"),
                    "timeline": True,
                    "steps": [{"label": f, "status": "ok"} for f in fixes],
                    "message": "Heal + sandbox retest",
                },
            }
        )
        events.append(_emit_progress(aios))
        return _finalize(events, True, redacted_message)

    if intent == "agent_run":
        goal = text
        if intent == "refine" and aios.get("goal"):
            goal = f"{aios.get('goal')}\n\nRefinement: {text}"
        # Also compile a workflow blueprint so deploy still works
        result = compile_solution_blueprint(db, workspace_id, goal)
        agent_meta = start_agent_os_plan(db, workspace_id=workspace_id, user_id=user_id, goal=goal)
        meta["aios"] = {
            "project_id": result.get("project_id"),
            "solution_id": result.get("solution_id"),
            "status": agent_meta.get("status") or "pending_approval",
            "goal": goal,
            "mode": "agent",
            "missing_credentials": result.get("missing_credentials") or [],
            "graph": result.get("graph") or {},
            "executable_preview": result.get("executable_preview") or {},
            "required_capabilities": result.get("required_capabilities") or [],
            "node_types": result.get("node_types") or [],
            "recipe": result.get("recipe"),
            "recipe_name": result.get("recipe_name"),
            "progress": agent_meta.get("progress") or progress_steps(mode="agent"),
            "next_action": agent_meta.get("next_action") or "approve",
            "approved": False,
            "tested": False,
            "heal_count": 0,
            "last_recipe": result.get("recipe_name") or (result.get("recipe") or {}).get("name"),
            "memory_hints": list(
                dict.fromkeys(
                    (aios.get("memory_hints") or [])
                    + ([f"recipe:{result.get('recipe_name')}"] if result.get("recipe_name") else [])
                )
            ),
            "agent_os": agent_meta,
        }
        _save_conv_meta(db, conv, meta)
        try:
            from app.composer.chat_actions import audit_chat_action

            audit_chat_action(
                db,
                action="agent_plan",
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type="solution",
                resource_id=str(result.get("solution_id") or ""),
            )
        except Exception:  # noqa: BLE001
            pass
        events.append({"type": "aios_solution", "data": {**meta["aios"], "tasks": agent_meta.get("tasks") or []}})
        if agent_meta.get("hitl"):
            events.append(
                {
                    "type": "aios_hitl",
                    "data": {
                        **agent_meta["hitl"],
                        "run_id": agent_meta.get("run_id"),
                        "message": "Agent OS paused for your approval.",
                    },
                }
            )
        else:
            events.append(_emit_progress(aios if aios else meta["aios"]))
        return _finalize(events, True, redacted_message)

    if intent in ("compose", "refine"):
        if is_vague_goal(text) and intent == "compose":
            events.append(clarify_event(text))
            return _finalize(events, True, redacted_message)
        try:
            from app.composer.chat_actions import audit_chat_action, check_compose_rate

            if not check_compose_rate(workspace_id, user_id):
                events.append(
                    {
                        "type": "aios_clarify",
                        "data": {
                            "message": "Rate limit — slow down compose requests for a minute.",
                            "chips": ["List my workflows", "What can you do?"],
                        },
                    }
                )
                return _finalize(events, True, redacted_message)
        except Exception:  # noqa: BLE001
            pass
        from app.composer.chat_requirements import parse_requirements as _parse_req_early

        goal = text
        fresh_hint = _parse_req_early(text, last_field=aios.get("last_field"), db=db)
        if intent == "compose" and fresh_hint.get("integration"):
            prev_int = (aios.get("requirements") or {}).get("integration")
            if prev_int and fresh_hint.get("integration") != prev_int and aios.get("solution_id"):
                events.append(
                    {
                        "type": "aios_solution",
                        "data": {
                            **aios,
                            "message": (
                                f"New topic **{fresh_hint.get('integration')}** detected — "
                                "starting a fresh blueprint (previous plan archived)."
                            ),
                            "status": "blueprint",
                            "phase": "blueprint",
                        },
                    }
                )
                aios["solution_id"] = None
                aios["approved"] = False
                aios["tested"] = False
            elif aios.get("goal") and (
                intent == "refine"
                or re.search(r"\b(for this|for that|from this)\b", text, re.I)
                or text.strip().lower() in ("build a workflow", "make a workflow", "build workflow")
            ):
                goal = aios.get("goal")
        elif aios.get("goal") and (
            intent == "refine"
            or re.search(r"\b(for this|for that|from this)\b", text, re.I)
            or text.strip().lower() in ("build a workflow", "make a workflow", "build workflow")
        ):
            goal = aios.get("goal")
        elif intent == "refine" and aios.get("goal"):
            goal = f"{aios.get('goal')}\n\nRefinement: {text}"
        # Follow-up with remembered field
        if aios.get("last_field") and re.search(r"\b(same|similar|another|also)\b", text, re.I):
            goal = f"[{aios.get('last_field')} field] {goal}"
        express = _wants_express(text, goal)
        t0 = time.perf_counter()
        from app.composer.gap_analysis import analyze_solution_gaps
        from app.composer.planner import infer_capabilities_from_goal
        from app.composer.workflow_composer import build_executable_graph
        from app.composer.recipes import match_recipe
        from app.composer.chat_requirements import (
            build_blueprint_preview,
            compose_goal_from_requirements,
            gather_prompt,
            merge_requirements_from_message,
            missing_workflow_slots,
            parse_requirements,
            sync_checklist_from_aios,
        )

        if aios.get("requirements") and intent in ("compose", "refine"):
            req = merge_requirements_from_message(dict(aios["requirements"]), goal, db=db)
        else:
            req = parse_requirements(goal, last_field=aios.get("last_field"), db=db)

        enriched_goal = compose_goal_from_requirements(req)
        recipe_goal = req.get("raw") or req.get("goal") or goal
        if req.get("integration"):
            recipe_goal = f"{req.get('integration')} {recipe_goal}"
        required_caps = infer_capabilities_from_goal(enriched_goal, force_workflow=True)
        live_missing = analyze_solution_gaps(db, workspace_id, required_caps)
        missing_slots = missing_workflow_slots(req)
        field = infer_field(enriched_goal, aios.get("last_field"))
        recipe = match_recipe(recipe_goal, fallback_generic=True)
        recipe_name = (recipe or {}).get("name")
        attach_n = _attachment_count(db, conversation_id, workspace_id)
        knowledge_id = aios.get("knowledge_id")
        if not knowledge_id and attach_n:
            knowledge_id = _attachment_knowledge_id(
                db, workspace_id=workspace_id, user_id=user_id, conversation_id=conversation_id
            )

        preview_executable = build_executable_graph(
            required_caps=required_caps,
            goal=enriched_goal,
            knowledge_id=knowledge_id,
            recipe_id=(recipe or {}).get("id"),
            requirements=req,
            db=db,
            workspace_id=workspace_id,
        )
        blueprint = build_blueprint_preview(
            enriched_goal, req, required_caps, preview_executable, missing_credentials=live_missing
        )
        compose_phase = "gather" if missing_slots or live_missing else "await_approve"
        next_action = "gather" if missing_slots else ("credentials" if live_missing else "approve")
        from app.composer.gap_analysis import credential_slots_for_missing

        from app.composer.chat_channels import friendly_title_for_goal

        friendly_title = req.get("workflow_name") or friendly_title_for_goal(enriched_goal)
        if req.get("integration") == "youtube":
            friendly_title = "YouTube channel workflow"
        elif req.get("integration") == "google_sheets":
            friendly_title = "Google Sheets workflow"
        if recipe_name and "generic" not in str(recipe_name).lower() and friendly_title == "Your automation plan":
            friendly_title = str(recipe_name)

        meta["aios"] = {
            "project_id": None,
            "solution_id": None,
            "status": "blueprint",
            "goal": enriched_goal,
            "mode": "workflow",
            "compose_phase": compose_phase,
            "phase": "blueprint",
            "missing_credentials": live_missing,
            "graph": {},
            "executable_preview": preview_executable,
            "required_capabilities": required_caps,
            "node_types": (preview_executable.get("meta") or {}).get("node_types") or [],
            "recipe": recipe,
            "recipe_name": recipe_name,
            "progress": progress_steps(missing_credentials=live_missing),
            "next_action": next_action,
            "approved": False,
            "tested": False,
            "heal_count": 0,
            "last_recipe": recipe_name,
            "last_field": field,
            "requirements": req,
            "blueprint": blueprint,
            "credential_slots": credential_slots_for_missing(live_missing),
            "knowledge_id": knowledge_id,
            "attachment_count": attach_n,
            "express": express,
            "friendly_title": friendly_title,
            "memory_hints": list(
                dict.fromkeys(
                    (aios.get("memory_hints") or [])
                    + ([f"recipe:{recipe_name}"] if recipe_name else [])
                    + ([f"field:{field}"] if field else [])
                    + ([f"knowledge:{knowledge_id}"] if knowledge_id else [])
                )
            ),
        }
        meta["aios"]["requirements"] = sync_checklist_from_aios(dict(req), meta["aios"])

        compose_ms = int((time.perf_counter() - t0) * 1000)
        meta["aios"]["compose_ms"] = compose_ms
        _save_conv_meta(db, conv, meta)
        try:
            from app.composer.chat_actions import audit_chat_action

            audit_chat_action(
                db,
                action="compose",
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type="blueprint",
                resource_id=str(req.get("id") or ""),
                detail={"recipe": recipe_name, "express": express, "compose_ms": compose_ms, "phase": compose_phase},
            )
        except Exception:  # noqa: BLE001
            pass

        missing = meta["aios"].get("missing_credentials") or []
        cred_chips = _build_cred_chips(required_caps, missing, missing_slots)

        solution_msg = gather_prompt(req, missing_slots, missing)
        preview_nodes = blueprint.get("preview_nodes") or preview_executable.get("nodes") or []
        preview_edges = blueprint.get("preview_edges") or preview_executable.get("edges") or []

        solution_card = {
            **meta["aios"],
            "friendly_title": friendly_title,
            "display_recipe": (
                None if recipe_name and "generic" in str(recipe_name).lower() else recipe_name
            ),
            "nodes": preview_nodes,
            "edges": preview_edges,
            "test_report": None,
            "credentials_url": "/credentials",
            "chips": cred_chips,
            "message": solution_msg,
        }
        node_types = [n.get("type") for n in preview_executable.get("nodes") or [] if isinstance(n, dict)]
        needs_custom_api = (
            req.get("integration") == "custom"
            or "cap_http" in required_caps
            or any(k in enriched_goal.lower() for k in ("custom api", "base_url", "stripe", "hubspot"))
        )
        if needs_custom_api and "api_node" not in node_types:
            http_node = next(
                (
                    n
                    for n in preview_executable.get("nodes") or []
                    if isinstance(n, dict) and n.get("type") == "http"
                ),
                None,
            )
            if http_node:
                http_data = http_node.get("data") or {}
                events.append(
                    {
                        "type": "aios_node_factory",
                        "data": {
                            "message": "No saved API node matched — probe your API, then save it to your node library.",
                            "suggested": {
                                "url": http_data.get("url") or "{{base_url}}",
                                "method": http_data.get("method") or "POST",
                                "body": http_data.get("body") or "{{output}}",
                                "auth": http_data.get("auth") or "custom",
                            },
                            "chips": ["Probe API", "Open workflow builder"],
                        },
                    }
                )
        events.append({"type": "aios_solution", "data": solution_card})
        return _finalize(events, True, redacted_message, goal=enriched_goal)

    if intent == "approve":
        has_blueprint = (
            aios.get("compose_phase") in ("gather", "await_approve", "blueprint")
            or aios.get("phase") == "blueprint"
            or aios.get("status") == "blueprint"
        )
        if not aios.get("solution_id") and not agent_os.get("plan_session_id") and not has_blueprint:
            events.append(
                {
                    "type": "aios_solution",
                    "data": {
                        "status": "error",
                        "message": "No pending plan to approve. Ask me to build a workflow first.",
                    },
                }
            )
            return _finalize(events, True, redacted_message)

        caps_check = list(aios.get("required_capabilities") or [])
        if caps_check:
            from app.composer.gap_analysis import analyze_solution_gaps
            from app.composer.chat_channels import friendly_missing_name, paste_hints_for_missing

            missing_now = analyze_solution_gaps(db, workspace_id, caps_check)
            aios["missing_credentials"] = missing_now
            if missing_now:
                meta["aios"] = aios
                _save_conv_meta(db, conv, meta)
                hints = paste_hints_for_missing(missing_now)
                names = ", ".join(friendly_missing_name(m) for m in missing_now[:4])
                if has_blueprint:
                    solution_card = _refresh_blueprint_from_aios(
                        db,
                        workspace_id=workspace_id,
                        conv=conv,
                        meta=meta,
                        aios=aios,
                    )
                    events.append(
                        {
                            "type": "aios_credentials_needed",
                            "data": {
                                "missing": missing_now,
                                "credentials_url": "/credentials",
                                "message": (
                                    f"Add credentials before approving (need: {names}). "
                                    "Paste them here or open Credentials."
                                ),
                                "chips": (hints[:1] if hints else []) + ["Open Credentials"],
                            },
                        }
                    )
                    events.append({"type": "aios_solution", "data": solution_card})
                else:
                    events.append(
                        {
                            "type": "aios_credentials_needed",
                            "data": {
                                "missing": missing_now,
                                "credentials_url": "/credentials",
                                "message": f"Add credentials before approving (need: {names}).",
                                "chips": (hints[:1] if hints else []) + ["Open Credentials"],
                            },
                        }
                    )
                return _finalize(events, True, redacted_message)

        materialized = False
        if not aios.get("solution_id") and has_blueprint and aios.get("mode") != "agent":
            from app.composer.chat_requirements import compose_goal_from_requirements, mark_checklist

            req = dict(aios.get("requirements") or {})
            enriched_goal = compose_goal_from_requirements(req)
            wf_name = req.get("workflow_name") or aios.get("friendly_title")
            result = compile_solution_blueprint(
                db,
                workspace_id,
                enriched_goal,
                requirements=req,
                materialize_workflow=True,
                workflow_name=wf_name,
            )
            mark_checklist(req, "plan", True)
            aios.update(
                {
                    "project_id": result.get("project_id"),
                    "solution_id": result.get("solution_id"),
                    "workflow_id": result.get("workflow_id"),
                    "goal": enriched_goal,
                    "missing_credentials": result.get("missing_credentials") or [],
                    "graph": result.get("graph") or {},
                    "executable_preview": result.get("executable_preview") or {},
                    "required_capabilities": result.get("required_capabilities") or [],
                    "node_types": result.get("node_types") or [],
                    "recipe": result.get("recipe"),
                    "recipe_name": result.get("recipe_name"),
                    "compose_phase": "built",
                    "phase": "built",
                    "status": "pending_approval",
                    "requirements": req,
                }
            )
            materialized = True

        aios["approved"] = True
        aios["status"] = "approved"
        aios["next_action"] = "test"
        # Refresh gaps from vault (do not block approve/test — sandbox is dry-run)
        if aios.get("required_capabilities"):
            from app.composer.gap_analysis import analyze_solution_gaps

            aios["missing_credentials"] = analyze_solution_gaps(
                db, workspace_id, aios.get("required_capabilities") or []
            )
        if isinstance(aios.get("requirements"), dict):
            from app.composer.chat_requirements import fulfillment_event, sync_checklist_from_aios

            aios["requirements"] = sync_checklist_from_aios(dict(aios["requirements"]), aios)
        report = None
        pending_agent_execute = aios.get("mode") == "agent" or (agent_os.get("mode") == "agent")

        if pending_agent_execute and agent_os.get("hitl", {}).get("status") == "pending":
            events.append(
                {
                    "type": "aios_hitl",
                    "data": {
                        **(agent_os.get("hitl") or {}),
                        "run_id": agent_os.get("run_id"),
                        "message": "Approve HITL (Continue) before agent execution.",
                    },
                }
            )
            meta["aios"] = aios
            _save_conv_meta(db, conv, meta)
            out = _finalize(events, True, redacted_message)
            return out

        if aios.get("solution_id") and not pending_agent_execute:
            report = _run_sandbox_for_aios(db, aios, workspace_id=workspace_id)
            aios["last_test"] = report
            aios["tested"] = report.get("status") == "success"
            aios["status"] = "tested" if aios["tested"] else "test_failed"
            aios["next_action"] = "deploy" if aios["tested"] else "heal"
            if not aios["tested"] and int(aios.get("heal_count") or 0) < 1:
                healed, report2, fixes = heal_and_retest(
                    aios.get("executable_preview") or {},
                    knowledge_id=aios.get("knowledge_id"),
                    missing_credentials=aios.get("missing_credentials") or [],
                )
                aios["executable_preview"] = healed
                aios["last_test"] = report2
                aios["tested"] = report2.get("status") == "success"
                aios["status"] = "tested" if aios["tested"] else "test_failed"
                aios["next_action"] = "deploy" if aios["tested"] else "heal"
                aios["heal_count"] = int(aios.get("heal_count") or 0) + 1
                events.append({"type": "aios_heal", "data": {"fixes": fixes, "status": "ok", "auto": True}})
                report = report2
            elif not aios["tested"]:
                events.append(
                    {
                        "type": "aios_heal",
                        "data": {
                            "status": "ask",
                            "message": "Sandbox failed. Tap Heal again if you want another repair pass.",
                        },
                    }
                )
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        events.append({"type": "aios_approved", "data": {"solution_id": aios.get("solution_id"), "status": "approved"}})
        if materialized:
            built_exec = aios.get("executable_preview") or {}
            events.append(
                {
                    "type": "aios_solution",
                    "data": {
                        **aios,
                        "phase": "built",
                        "nodes": built_exec.get("nodes") or [],
                        "edges": built_exec.get("edges") or [],
                        "message": (
                            f"Workflow **{aios.get('friendly_title') or 'ready'}** built — "
                            "review the graph below, then run a test."
                        ),
                        "chips": ["Run test", "Deploy"],
                    },
                }
            )
        if report is not None:
            events.append({"type": "aios_test_report", "data": report})
            events.append(
                {
                    "type": "aios_sandbox",
                    "data": {
                        **report,
                        "primary": "Deploy" if report.get("status") == "success" else "Heal & retest",
                        "chips": (
                            ["Deploy", "Retest"]
                            if report.get("status") == "success"
                            else ["Heal & retest", "Retest"]
                        ),
                    },
                }
            )
            events.append(
                {
                    "type": "aios_run_status",
                    "data": {
                        "status": report.get("status"),
                        "timeline": True,
                        "message": "Enterprise sandbox suite",
                        "node_count": report.get("node_count"),
                        "passed": report.get("passed"),
                        "failed": report.get("failed"),
                    },
                }
            )
        events.append(_emit_progress(aios))
        out = _finalize(events, True, redacted_message)
        if pending_agent_execute:
            out["pending_agent_execute"] = True
            out["agent_goal"] = aios.get("goal") or text
            out["agent_knowledge_id"] = aios.get("knowledge_id")
            out["agent_os"] = agent_os
        return out

    if intent == "test":
        if not aios.get("solution_id"):
            events.append(
                {
                    "type": "aios_test_report",
                    "data": {"status": "failed", "logs": ["No pending solution to test. Compose a plan first."]},
                }
            )
            return _finalize(events, True, redacted_message)
        # Allow retest after express compose even if not yet HITL-approved
        if not aios.get("approved") and not aios.get("express") and aios.get("status") not in (
            "tested",
            "test_failed",
        ):
            events.append(
                {
                    "type": "aios_solution",
                    "data": {
                        **aios,
                        "message": "Approve the plan before running a sandbox test.",
                        "status": "pending_approval",
                    },
                }
            )
            return _finalize(events, True, redacted_message)
        report = _run_sandbox_for_aios(db, aios, workspace_id=workspace_id)
        aios["last_test"] = report
        aios["tested"] = report.get("status") == "success"
        aios["status"] = "tested" if aios["tested"] else "test_failed"
        aios["next_action"] = "deploy" if aios["tested"] else "heal"
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        events.append({"type": "aios_test_report", "data": report})
        events.append(
            {
                "type": "aios_sandbox",
                "data": {
                    **report,
                    "primary": "Deploy" if report.get("status") == "success" else "Heal & retest",
                    "chips": (
                        ["Deploy", "Retest"]
                        if report.get("status") == "success"
                        else ["Heal & retest", "Retest"]
                    ),
                },
            }
        )
        if not aios["tested"]:
            events.append(
                {
                    "type": "aios_heal",
                    "data": {
                        "status": "suggested",
                        "message": "Test failed. Tap Heal to repair the graph and retest.",
                    },
                }
            )
        events.append(_emit_progress(aios))
        return _finalize(events, True, redacted_message)

    if intent == "deploy":
        from app.composer.chat_requirements import check_chat_policy, fulfillment_event, sync_checklist_from_aios

        policy_block = check_chat_policy(db, workspace_id=workspace_id, action="deploy")
        if policy_block:
            return _finalize(policy_block.get("events") or [], True, redacted_message)

        solution_id = aios.get("solution_id")
        if not solution_id:
            events.append(
                {
                    "type": "aios_deploy",
                    "data": {"status": "error", "message": "No solution to deploy. Compose and approve a plan first."},
                }
            )
            return _finalize(events, True, redacted_message)
        if not aios.get("approved"):
            events.append(
                {
                    "type": "aios_solution",
                    "data": {
                        **aios,
                        "message": "Approve the plan before deploy.",
                        "status": "pending_approval",
                    },
                }
            )
            return _finalize(events, True, redacted_message)

        force_deploy = bool(re.search(r"\bforce deploy\b", text or "", re.I))
        if not aios.get("tested") and not force_deploy:
            events.append(
                {
                    "type": "aios_deploy",
                    "data": {
                        "status": "blocked",
                        "message": "Run a sandbox test before deploy, or say **force deploy** to skip.",
                        "chips": ["Run test", "Retest", "force deploy"],
                    },
                }
            )
            return _finalize(events, True, redacted_message)

        knowledge_id = aios.get("knowledge_id") or _attachment_knowledge_id(
            db, workspace_id=workspace_id, user_id=user_id, conversation_id=conversation_id
        )
        if knowledge_id:
            aios["knowledge_id"] = knowledge_id

        deploy = deploy_solution_graph(
            db,
            workspace_id,
            solution_id,
            user_id=user_id,
            knowledge_id=knowledge_id,
        )
        if (aios.get("executable_preview") or {}).get("meta", {}).get("schedule_note"):
            deploy = {
                **deploy,
                "schedule_note": aios["executable_preview"]["meta"]["schedule_note"],
                "links": {
                    **(deploy.get("links") or {}),
                    "schedules": "/workflows?tab=schedules",
                },
            }
        aios["deploy"] = deploy
        aios["status"] = deploy.get("status")
        aios["next_action"] = "done"
        if aios.get("agent_os"):
            aios["agent_os"]["status"] = "done"
        if isinstance(aios.get("requirements"), dict):
            aios["requirements"] = sync_checklist_from_aios(dict(aios["requirements"]), aios)
        meta["aios"] = aios
        _save_conv_meta(db, conv, meta)
        try:
            from app.composer.chat_actions import audit_chat_action

            audit_chat_action(
                db,
                action="deploy",
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type="workflow",
                resource_id=str(deploy.get("workflow_id") or ""),
            )
        except Exception:  # noqa: BLE001
            pass
        events.append({"type": "aios_deploy", "data": {**deploy, "chips": ["Run now", "Schedule", "Run test"]}})
        events.append(_emit_progress(aios))
        if isinstance(aios.get("requirements"), dict):
            events.append(
                fulfillment_event(
                    aios["requirements"],
                    message="Requirements fulfillment complete after deploy."
                    if (aios.get("status") in ("deployed", "done"))
                    else "Deploy finished — checklist updated.",
                )
            )
        return _finalize(events, True, redacted_message)

    out = _finalize(events, blocked_normal_reply, redacted_message)
    if route_info.get("suggest_workflow_chips") and not blocked_normal_reply and not events:
        out["suggest_workflow_chips"] = True
        out["suggest_chips"] = [
            f"Build a workflow for this: {text[:120]}",
            "Enterprise playbooks",
            "What can you do?",
        ]
    return out


def _finalize(
    events: list[dict[str, Any]],
    blocked_normal_reply: bool,
    redacted_message: str,
    *,
    goal: str = "",
) -> dict[str, Any]:
    summary = ""
    primary = _select_primary_event(events) if events else None
    ui_events = _ui_events_from(events) if blocked_normal_reply else list(events or [])
    if blocked_normal_reply and events:
        from app.composer.chat_narrative import friendly_summary

        tech = bool(re.search(r"\b(show tech|tech details|show ids|debug ids)\b", redacted_message or "", re.I))
        # Prefer primary-only for friendlier one-paragraph replies
        summary = friendly_summary(
            ui_events or events,
            goal=goal or redacted_message or "",
            tech_details=tech,
        )
        if not (summary or "").strip():
            summary = "Done — use the buttons on the card."

    return {
        "events": events,
        "ui_events": ui_events,
        "primary_event": primary,
        "blocked_normal_reply": blocked_normal_reply,
        "summary": summary,
        "redacted_message": redacted_message,
    }


def _aios_public_snapshot(aios: dict[str, Any] | None) -> dict[str, Any]:
    """Lightweight aios fields needed by WebSocket / same-turn LLM."""
    if not aios:
        return {}
    return {
        "conversation_api_key": aios.get("conversation_api_key"),
        "compose_phase": aios.get("compose_phase"),
        "status": aios.get("status"),
        "solution_id": aios.get("solution_id"),
        "workflow_id": (aios.get("deploy") or {}).get("workflow_id"),
        "missing_credentials": aios.get("missing_credentials"),
    }


async def process_chat_turn(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    workspace_role: str | None = "editor",
) -> dict[str, Any]:
    """Async chat pipeline: bridge → ops dispatch → optional Agent OS execute."""
    def _attach_aios_snapshot(out: dict[str, Any]) -> dict[str, Any]:
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                try:
                    meta = json.loads(conv.meta_json or "{}")
                except json.JSONDecodeError:
                    meta = {}
                snap = _aios_public_snapshot(meta.get("aios") or {})
                if snap:
                    out["aios"] = snap
        return out

    bridge = process_chat_goal(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=user_message,
    )

    if bridge.get("needs_ops_dispatch"):
        from app.composer.chat_actions import dispatch_ops_action

        ops = await dispatch_ops_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=bridge.get("ops_intent"),
            workspace_role=workspace_role,
        )
        if ops:
            evs = ops.get("events") or []
            out = _finalize(
                evs,
                bool(ops.get("blocked_normal_reply")),
                bridge.get("redacted_message") or user_message,
            )
            if ops.get("summary"):
                out["summary"] = ops["summary"]
            return _attach_aios_snapshot(out)

    events = list(bridge.get("events") or [])
    summary = bridge.get("summary") or ""
    blocked = bool(bridge.get("blocked_normal_reply"))
    primary = bridge.get("primary_event")
    ui_events = bridge.get("ui_events")
    # Soft suggest chips for QA turns with work verbs (frontend also paints defaults)
    if bridge.get("suggest_workflow_chips") and not blocked:
        events.append(
            {
                "type": "aios_suggest",
                "data": {
                    "message": "I can also turn this into a workflow.",
                    "chips": bridge.get("suggest_chips")
                    or [
                        "Build a workflow for this",
                        "Enterprise playbooks",
                        "What can you do?",
                    ],
                },
            }
        )

    if bridge.get("pending_agent_execute"):
        from app.agent_os.integration import execute_agent
        from app.composer.chat_actions import audit_chat_action, build_platform_ctx
        from app.services.agent_tools import DEFAULT_AGENT_SYSTEM

        goal = bridge.get("agent_goal") or user_message
        events.append(
            {
                "type": "aios_agent_progress",
                "data": {
                    "message": "Agent OS executing…",
                    "goal": goal,
                    "tasks": (bridge.get("agent_os") or {}).get("tasks") or [],
                },
            }
        )
        try:
            ctx = build_platform_ctx(db, user_id=user_id, workspace_id=workspace_id)
            result = await execute_agent(
                db,
                ctx,
                user_input=goal,
                tools=["summarize", "kb_search"],
                system=DEFAULT_AGENT_SYSTEM,
                knowledge_id=bridge.get("agent_knowledge_id"),
                conversation_id=conversation_id,
                mode="single",
                agent_type="supervisor",
            )
            events.append(
                {
                    "type": "aios_agent_result",
                    "data": {
                        "output": result.get("output") or "",
                        "run_id": result.get("run_id"),
                        "confidence": result.get("confidence"),
                        "selected_tools": result.get("selected_tools") or [],
                        "verification": result.get("verification"),
                    },
                }
            )
            audit_chat_action(
                db,
                action="agent_execute",
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type="agent_run",
                resource_id=str(result.get("run_id") or ""),
            )
            out_snip = (result.get("output") or "")[:500]
            summary = (summary + "\n" if summary else "") + (out_snip or "Agent finished.")
            blocked = True
        except Exception as exc:  # noqa: BLE001
            logger.exception("agent execute failed")
            events.append(
                {
                    "type": "aios_agent_result",
                    "data": {"status": "error", "output": str(exc)[:500]},
                }
            )
            summary = (summary + "\n" if summary else "") + f"Agent failed: {exc}"
            blocked = True

    # Re-pack so agent extras still collapse to one UI card
    if events != list(bridge.get("events") or []) or bridge.get("pending_agent_execute"):
        packed = _finalize(
            events,
            blocked,
            bridge.get("redacted_message") or user_message,
            goal=bridge.get("agent_goal") or "",
        )
        if summary.strip():
            packed["summary"] = summary.strip()
        return _attach_aios_snapshot(packed)

    return _attach_aios_snapshot({
        "events": events,
        "ui_events": ui_events if ui_events is not None else _ui_events_from(events),
        "primary_event": primary or _select_primary_event(events),
        "blocked_normal_reply": blocked,
        "summary": summary.strip(),
        "redacted_message": bridge.get("redacted_message") or user_message,
    })
