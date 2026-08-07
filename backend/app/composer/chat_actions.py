"""Unified chat action bus — workflow/knowledge/capability ops for Peak Chat."""

from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.database import Conversation, KnowledgeBase, KnowledgeFile, User, Workflow, WorkflowRun, Workspace
from app.security.audit import audit_log
from app.security.rate_limit import rate_limiter
from app.services.knowledge import process_file_record

logger = logging.getLogger(__name__)

OPS_INTENTS = frozenset(
    {
        "run_workflow",
        "run_workflows_parallel",
        "test_workflow",
        "list_workflows",
        "workflow_status",
        "stop_run",
        "delete_workflow",
        "update_workflow",
        "clone_workflow",
        "use_knowledge",
        "index_attachment",
        "list_credentials_needed",
        "capabilities",
        "monitor",
        # Enterprise Chat OS
        "list_schedules",
        "schedule_create",
        "schedule_pause",
        "compliance_report",
        "finops_summary",
        "workspace_health",
        "list_recommendations",
        "approve_recommendation",
        "export_conversation",
        "share_conversation",
        "title_conversation",
        "tag_conversation",
        "summarize_conversation",
        "audit_trail",
        "vault_posture",
        "integrations_health",
        "test_notification",
        "playbook",
        # Requirements fulfillment
        "capture_requirements",
        "show_requirements",
        "fulfill_requirements",
        "show_policy",
        # Chat Powerhouse (12 mega tools)
        "powerhouse_catalog",
        "workflow_diff",
        "version_time_machine",
        "restore_version",
        "eval_command",
        "cost_receipt",
        "run_debugger",
        "knowledge_graph",
        "collab_war_room",
        "incident_kill_switch",
        "simulate_lab",
        "sla_brief",
        "change_request",
        "apply_change_request",
        "action_digest",
        # Chat Autopilot
        "autopilot_start",
        "autopilot_confirm",
        "autopilot_status",
        "autopilot_cancel",
        "autopilot_next",
        "autopilot_skip",
        # Chat Forge (12 tools)
        "forge_catalog",
        "prompt_drift",
        "ab_router",
        "webhook_studio",
        "project_packs",
        "publish_scan",
        "template_reuse",
        "model_lab_desk",
        "ocr_to_workflow",
        "issue_bridge",
        "csv_import_chat",
        "solution_docs",
        "solution_assert",
        # API node factory (chat)
        "node_probe",
        "node_create",
        "node_test",
        "node_publish",
        "node_attach_to_workflow",
        "openapi_import",
        # Navigation
        "open_marketplace",
        "open_settings",
        "open_model_lab",
        "open_credentials",
        # Knowledge + LLM planning
        "store_chat_knowledge",
        "list_llm_providers",
        "switch_planning_model",
        "use_workspace_llm",
        "requirements_confirm",
        "create_component",
    }
)


def build_platform_ctx(db: Session, *, user_id: int, workspace_id: int):
    """Minimal PlatformContext for chat WS / background paths."""
    from app.platform.access import PlatformContext

    user = db.get(User, user_id)
    workspace = db.get(Workspace, workspace_id)
    if not user or not workspace:
        raise ValueError("User or workspace not found")
    return PlatformContext(
        user=user,
        workspace=workspace,
        workspace_id=workspace_id,
        role="editor",
        db=db,
    )


def check_compose_rate(workspace_id: int, user_id: int) -> bool:
    """Soft per-workspace rate for expensive compose/deploy actions."""
    key = f"ws:{workspace_id}:user:{user_id}"
    return rate_limiter.allow("chat_compose", key, limit=30, window_seconds=60)


def audit_chat_action(
    db: Session,
    *,
    action: str,
    user_id: int,
    workspace_id: int,
    resource_type: str = "",
    resource_id: str = "",
    detail: dict | None = None,
    success: bool = True,
) -> None:
    audit_log(
        db,
        action=f"chat.{action}",
        actor_user_id=user_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=str(resource_id or ""),
        success=success,
        detail=detail or {},
    )
    if action in ("compose", "deploy", "run_workflow", "approve", "test"):
        try:
            conv_id = (detail or {}).get("conversation_id")
            if conv_id:
                conv, aios = _load_aios(db, conv_id)
                if conv and aios.get("last_receipt"):
                    aios.setdefault("ops_finops", []).append(
                        {
                            "action": action,
                            "est_cost_usd": aios["last_receipt"].get("est_cost_usd"),
                            "at": aios["last_receipt"].get("at"),
                        }
                    )
                    _save_aios(db, conv, aios)
        except Exception:  # noqa: BLE001
            pass


def classify_ops_intent(text: str) -> str | None:
    t = (text or "").lower().strip()
    if not t:
        return None
    from app.composer.chat_autopilot import classify_autopilot_intent
    from app.composer.chat_forge import classify_forge_intent
    from app.composer.chat_powerhouse import classify_power_intent
    from app.composer.chat_node_factory import classify_nav_intent, classify_node_factory_intent

    nf = classify_node_factory_intent(text)
    if nf:
        return nf
    nav = classify_nav_intent(text)
    if nav:
        return nav
    auto = classify_autopilot_intent(text)
    if auto:
        return auto
    forge = classify_forge_intent(text)
    if forge:
        return forge
    power = classify_power_intent(text)
    if power:
        return power
    if re.search(r"\bwhat can you do\b|\bcapabilities\b|\bhelp me with chat\b", t):
        return "capabilities"
    if re.search(r"\bcapture requirements\b|\brecord requirements\b|\bsave requirements\b|\brequirements\s*:", t):
        return "capture_requirements"
    if re.search(r"\bshow requirements\b|\blist requirements\b|\bmy requirements\b|\brequirements brief\b", t):
        return "show_requirements"
    if re.search(r"\bfulfill (these )?requirements\b|\bfulfill requirements\b|\bcomplete (these )?requirements\b", t):
        return "fulfill_requirements"
    if re.search(r"\bchat policy\b|\bshow (workspace )?polic(y|ies)\b|\bpolicy status\b", t):
        return "show_policy"
    if re.search(r"\brun (incident|weekly|onboard|ops).{0,20}playbook\b|\brun .{0,20}playbook\b|\benterprise playbooks?\b|\blist (enterprise )?playbooks\b|\bincident playbook\b|\bweekly ops digest playbook\b|\bonboard new bot playbook\b", t):
        return "playbook"
    if re.search(r"\blist schedules\b|\bshow schedules\b|\bmy schedules\b", t):
        return "list_schedules"
    if re.search(r"\bpause schedule\b|\bdisable schedule\b", t):
        return "schedule_pause"
    if re.search(r"\bschedule (my )?(last )?workflow\b|\bschedule .{0,40} (daily|weekly|every)\b|\bschedule .{0,40} at \d", t):
        return "schedule_create"
    if re.search(r"\bcompliance report\b|\bsecurity posture\b", t):
        return "compliance_report"
    if re.search(r"\bfinops\b|\bai costs?\b|\bcost summary\b|\bshow (ai )?costs\b", t):
        return "finops_summary"
    if re.search(r"\bworkspace health\b|\bhealth report\b", t):
        return "workspace_health"
    if re.search(r"\bapprove recommendation\b", t):
        return "approve_recommendation"
    if re.search(r"\bshow recommendations\b|\blist recommendations\b|\bopen recommendations\b", t):
        return "list_recommendations"
    if re.search(r"\bexport (this )?(chat|conversation)\b", t):
        return "export_conversation"
    if re.search(r"\bshare (this )?(chat|conversation)\b", t):
        return "share_conversation"
    if re.search(r"\btitle (this )?(chat|conversation)\b|\bgenerate (a )?title\b", t):
        return "title_conversation"
    if re.search(r"\btag (this )?(chat|conversation)\b|\bsuggest tags\b", t):
        return "tag_conversation"
    if re.search(r"\bsummarize (this )?(chat|thread|conversation)\b", t):
        return "summarize_conversation"
    if re.search(r"\baudit (log|trail)\b|\bshow my recent chat actions\b|\brecent chat actions\b", t):
        return "audit_trail"
    if re.search(r"\blist vault\b|\bvault categories\b|\bvault posture\b", t):
        return "vault_posture"
    if re.search(r"\bsend a test notification\b|\btest notification\b", t):
        return "test_notification"
    if re.search(r"\bcheck (slack|telegram|integrations?)\b|\bintegrations? (health|status)\b", t):
        return "integrations_health"
    if re.search(r"\bcreate component\b|\bmake component\b|\bnew component\b|\bbuild component\b", t):
        return "create_component"
    if re.search(r"\bstore (this |that )?(data |info |summary )?in knowledge\b|\bsave to knowledge\b|\badd to knowledge\b|\bstore (this |that )?data in knowlage\b", t):
        return "store_chat_knowledge"
    if re.search(r"\blist (my )?models\b|\blist (my )?providers\b|\bwhich api keys\b|\bshow providers\b", t):
        return "list_llm_providers"
    if re.search(r"\buse workspace (default |model|llm)\b|\buse default provider\b", t):
        return "use_workspace_llm"
    if re.search(r"\buse model\b|\bswitch to\b", t) and not re.search(r"\bworkflow\b", t):
        return "switch_planning_model"
    if re.search(r"\byes build this\b|\bbuild this plan\b|\bconfirm (this )?plan\b", t):
        return "requirements_confirm"
    if re.search(
        r"\blist (my )?workflows\b|\bshow (my )?workflows\b|\bmy workflows\b|"
        r"\bshow me my workflow\b|\bshow my workflow\b|\bhow many workflows?\b|\bworkflow count\b|"
        r"\btotal workflows?\b|\bgive me total workflows?\b|\bhow many workflow\b",
        t,
    ):
        return "list_workflows"
    if re.search(r"\b(status of|workflow status|last run|run status)\b", t):
        return "workflow_status"
    if re.search(r"\bstop (this |the )?(run|workflow)\b", t):
        return "stop_run"
    if re.search(r"\btest (my )?(last )?workflow\b|\btest workflow\b|\bsandbox test\b", t):
        return "test_workflow"
    if re.search(
        r"\brun workflows\b|\brun workflow\s+\d+.*\band\b|\bworkflow\s+\d+.*,.*workflow|"
        r"\brun workflow\s+\d+\s+and\s+\d+",
        t,
    ):
        return "run_workflows_parallel"
    if re.search(r"\brun (my )?(last )?workflow\b|\brun workflow\b|\brun it\b|\bexecute it\b|\brun this\b", t):
        return "run_workflow"
    if re.search(r"\bindex (my )?attachments?\b|\bindex (these|the) files?\b", t):
        return "index_attachment"
    if re.search(r"\buse knowledge\b|\buse (the )?knowledge base\b|\blink knowledge\b", t):
        return "use_knowledge"
    if re.search(r"\b(delete|remove|drop)\b.*\bworkflow\b|\bdelete (my )?workflow\b", t):
        return "delete_workflow"
    if re.search(r"\bclone (my )?(last )?workflow\b|\bduplicate workflow\b", t):
        return "clone_workflow"
    if re.search(r"\b(update|refresh|sync) (my )?(last )?workflow\b", t):
        return "update_workflow"
    if re.search(r"\bmonitor (the )?(run|workflow)\b|\brun timeline\b", t):
        return "monitor"
    return None


def _load_aios(db: Session, conversation_id: str | None) -> tuple[Conversation | None, dict[str, Any]]:
    if not conversation_id:
        return None, {}
    conv = db.get(Conversation, conversation_id)
    if not conv:
        return None, {}
    try:
        meta = json.loads(conv.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    aios = meta.get("aios") if isinstance(meta.get("aios"), dict) else {}
    return conv, aios


def _save_aios(db: Session, conv: Conversation | None, aios: dict[str, Any]) -> None:
    if not conv:
        return
    try:
        meta = json.loads(conv.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta["aios"] = aios
    conv.meta_json = json.dumps(meta)
    db.commit()


def _find_workflow(db: Session, workspace_id: int, text: str, aios: dict) -> Workflow | None:
    # Prefer workflow from current AIOS session
    wid = aios.get("workflow_id")
    if wid:
        wf = db.get(Workflow, wid)
        if wf and int(wf.workspace_id or 0) == int(workspace_id):
            return wf
    # Prefer last deployed from conversation
    deploy = aios.get("deploy") or {}
    wid = deploy.get("workflow_id")
    if wid:
        wf = db.get(Workflow, wid)
        if wf and int(wf.workspace_id or 0) == int(workspace_id):
            return wf
    # Name / id from message
    m = re.search(r"workflow\s+[\"']?([a-zA-Z0-9_\- ]{2,80})", text or "", re.I)
    needle = (m.group(1).strip() if m else "").lower()
    q = db.query(Workflow).filter(Workflow.workspace_id == workspace_id, Workflow.status == 1)
    rows = q.order_by(Workflow.update_time.desc()).limit(50).all()
    if not rows:
        return None
    if not needle or needle in ("last", "my last", "latest"):
        return rows[0]
    for wf in rows:
        if needle in (wf.name or "").lower() or needle == str(wf.id).lower():
            return wf
    return rows[0]


def _parse_workflow_needles(text: str) -> list[str]:
    """Extract workflow name/id needles for parallel runs (e.g. workflow 1 and 3)."""
    t = (text or "").lower()
    needles: list[str] = []
    for m in re.finditer(r"workflow\s*#?\s*([a-z0-9_\-]+)", t, re.I):
        val = m.group(1).strip()
        if val and val not in needles:
            needles.append(val)
    if len(needles) >= 2:
        return needles
    if " and " in t or "," in t:
        for m in re.finditer(r"\b(\d+)\b", t):
            val = m.group(1)
            if val not in needles:
                needles.append(val)
    return needles[:5]


def _find_workflows_by_needles(
    db: Session,
    workspace_id: int,
    needles: list[str],
    aios: dict,
) -> list[Workflow]:
    if not needles:
        wf = _find_workflow(db, workspace_id, "", aios)
        return [wf] if wf else []
    q = db.query(Workflow).filter(Workflow.workspace_id == workspace_id, Workflow.status == 1)
    rows = q.order_by(Workflow.update_time.desc()).limit(50).all()
    found: list[Workflow] = []
    for needle in needles:
        n = needle.lower().strip()
        for wf in rows:
            if wf in found:
                continue
            if n == str(wf.id).lower() or n in (wf.name or "").lower():
                found.append(wf)
                break
    return found


def capabilities_event() -> dict[str, Any]:
    return {
        "type": "aios_capabilities",
        "data": {
            "title": "What Peak Chat can do",
            "skills": [
                "Universal workflow composer — trigger → process → notify/output for any business field",
                "25+ recipes + LLM graph planner + generic fallback for novel automations",
                "Custom SaaS via API Node Factory, OpenAPI import, and HTTP nodes",
                "Chat Powerhouse — 12 mega tools (diff, versions, eval, cost, debug, KG, collab, kill switch, simulate, SLA, change requests, digests)",
                "Chat Autopilot — multi-step playbooks with confirm gates (incident / weekly / onboard)",
                "Chat Forge — 12 tools (drift, A/B, webhooks, projects, publish scan, reuse, model lab, OCR, GitHub issues, CSV, docs, assertions)",
                "Requirements brief → confirm → blueprint → approve → sandbox test → deploy → run",
                "Hybrid LLM: your API key, vault, or workspace default for planning",
                "Agent OS research plans with human approval",
                "List / run / monitor / schedule workspace workflows from chat",
                "Knowledge: upload, index attachments, store chat notes, RAG in workflows",
                "Enterprise EIAP: compliance, FinOps, health, audit, export/share",
            ],
            "can_build": [
                "Email / Gmail / Outlook digests and alerts",
                "Slack, Discord, Telegram, WhatsApp bots and notifications",
                "GitHub / Jira / Linear triage and issue workflows",
                "Google Sheets, Calendar, Drive, YouTube, Shopify integrations",
                "Webhook / HTTP / custom API automations",
                "Knowledge RAG + LLM processing pipelines",
                "Multi-agent supervisor workflows",
                "Scheduled jobs (cron via chat after deploy)",
            ],
            "needs_credentials": [
                "SMTP / Gmail app passwords, Slack/Telegram tokens, API keys",
                "Google / Microsoft OAuth tokens in Credentials (link from chat)",
                "Custom API keys via vault or paste-in-chat (real secrets, not hints)",
            ],
            "needs_express": [
                "Say express compose to skip requirements brief and fast-path test",
                "High-confidence recipe matches can auto-test in one turn",
            ],
            "workflow_types": [
                {"id": "email", "label": "Email workflow", "chip": "Build an email digest workflow"},
                {"id": "slack", "label": "Slack bot", "chip": "Build a Slack alert workflow"},
                {"id": "webhook", "label": "Webhook", "chip": "Build a webhook automation workflow"},
                {"id": "custom_api", "label": "Custom API", "chip": "Build a workflow for a custom API"},
                {"id": "agent", "label": "Agent", "chip": "Build a multi-agent research workflow"},
                {"id": "schedule", "label": "Scheduled job", "chip": "Build a daily scheduled workflow"},
                {"id": "knowledge", "label": "Knowledge RAG", "chip": "Build a workflow that answers from my knowledge base"},
            ],
            "cannot": [
                "Control your PC shell, desktop, or browser outside NovaFlow",
                "Run arbitrary code, shell scripts, or arbitrary visual-editor nodes not in the runtime palette",
                "Complete OAuth provider login inside chat (use Credentials with return-to-chat links)",
                "Guarantee perfect graphs for every novel request without confirm + sandbox test",
                "Bypass workspace RBAC or enforce policies (viewer cannot run/deploy)",
            ],
            "chips": [
                "Build an email digest workflow",
                "Build a Slack alert workflow",
                "Build a custom API workflow",
                "Show powerhouse",
                "Show forge",
                "Run incident autopilot",
            ],
        },
    }


def list_workflows_event(db: Session, workspace_id: int) -> dict[str, Any]:
    rows = (
        db.query(Workflow)
        .filter(Workflow.workspace_id == workspace_id, Workflow.status == 1)
        .order_by(Workflow.update_time.desc())
        .limit(12)
        .all()
    )
    items = [{"id": w.id, "name": w.name, "link": f"/workflows/{w.id}"} for w in rows]
    total = (
        db.query(Workflow)
        .filter(Workflow.workspace_id == workspace_id, Workflow.status == 1)
        .count()
    )
    return {
        "type": "aios_workflows",
        "data": {
            "workflows": items,
            "count": total,
            "message": f"You have **{total}** published workflow(s). Showing latest {len(items)}.",
        },
    }


async def run_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, text, aios)
    if not wf:
        return {
            "events": [
                {
                    "type": "aios_run_status",
                    "data": {"status": "error", "message": "No workflow found. Deploy one from chat first."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No workflow found to run.",
        }
    from app.services.workflow import run_workflow_with_progress
    from app.services.workflow_run_cancel import clear_run, register_run

    user_input = text
    m = re.search(r"with input[:\s]+(.+)$", text or "", re.I)
    if m:
        user_input = m.group(1).strip()
    elif re.match(r"^\s*run (my )?(last )?workflow", text or "", re.I):
        user_input = aios.get("goal") or "Run from chat"

    conversation_api_key = aios.get("conversation_api_key")
    cancel_event = register_run(workspace_id, user_id)
    progress_events: list[dict[str, Any]] = []

    async def _emit(event: dict):
        progress_events.append(event)

    try:
        result = await run_workflow_with_progress(
            db,
            wf,
            user_id,
            user_input,
            _emit,
            workspace_id,
            conversation_api_key=conversation_api_key,
            cancel_event=cancel_event,
        )
    finally:
        clear_run(workspace_id, user_id)
    status = result.get("status") or ("pending_human" if result.get("pending_run_id") else "completed")
    if result.get("steps") and any(s.get("status") == "error" for s in (result.get("steps") or []) if isinstance(s, dict)):
        status = "failed"
    run_id = None
    # latest run for this workflow
    last = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_id == wf.id)
        .order_by(WorkflowRun.create_time.desc())
        .first()
    )
    if last:
        run_id = last.id
    aios["active_run_id"] = run_id
    aios["last_workflow_id"] = wf.id
    aios["last_run"] = {
        "workflow_id": wf.id,
        "run_id": run_id,
        "status": status,
        "output": (result.get("output") or "")[:500],
    }
    _save_aios(db, conv, aios)
    audit_chat_action(
        db,
        action="run_workflow",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="workflow",
        resource_id=wf.id,
        detail={"run_id": run_id, "status": status},
    )
    event = {
        "type": "aios_run_status",
        "data": {
            "status": status,
            "workflow_id": wf.id,
            "workflow_name": wf.name,
            "run_id": run_id,
            "output": (result.get("output") or "")[:800],
            "steps": (result.get("steps") or [])[:20],
            "progress": [
                {"type": "aios_run_step", "phase": e.get("phase"), "step": e.get("step")}
                for e in progress_events
                if e.get("type") == "step"
            ][:40],
            "links": {"workflow": f"/workflows/{wf.id}"},
            "pending_run_id": result.get("pending_run_id"),
        },
    }
    step_events = [
        {"type": "aios_run_step", "phase": e.get("phase"), "step": e.get("step")}
        for e in progress_events
        if e.get("type") == "step"
    ][:40]
    human_review = next((e for e in progress_events if e.get("type") == "human_review"), None)
    out_events: list[dict[str, Any]] = step_events[:40]
    if human_review:
        out_events.append({"type": "aios_human_review", "data": human_review})
    out_events.append(event)
    summary = f"Ran workflow **{wf.name}** — status: {status}."
    return {"events": out_events, "blocked_normal_reply": True, "summary": summary}


async def test_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, text, aios)
    if not wf:
        return {
            "events": [
                {
                    "type": "aios_test_report",
                    "data": {"status": "failed", "message": "No published workflow found to test."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No workflow found to test.",
        }
    try:
        graph = json.loads(wf.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    from app.sandbox.enterprise_suite import run_enterprise_suite

    report = run_enterprise_suite(
        graph,
        field="generic",
        db=db,
        workspace_id=workspace_id,
        live_credential_probe=True,
    )
    ok = report.get("status") == "success"
    aios["last_test"] = {
        "workflow_id": wf.id,
        "ok": ok,
        "score": report.get("score"),
    }
    _save_aios(db, conv, aios)
    audit_chat_action(
        db,
        action="test_workflow",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="workflow",
        resource_id=wf.id,
        detail={"ok": ok, "score": report.get("score")},
    )
    msg = "Sandbox test passed." if ok else "Sandbox test reported issues — open the workflow builder to fix nodes."
    return {
        "events": [
            {
                "type": "aios_test_report",
                "data": {
                    **report,
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "message": msg,
                    "links": {"workflow": f"/workflows/{wf.id}"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Test **{wf.name}**: {'passed' if ok else 'issues found'}.",
    }


async def run_workflows_parallel_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    needles = _parse_workflow_needles(text)
    workflows = _find_workflows_by_needles(db, workspace_id, needles, aios)
    if not workflows:
        return {
            "events": [
                {
                    "type": "aios_run_status",
                    "data": {"status": "error", "message": "No matching published workflows found."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No workflows matched for parallel run.",
        }
    from app.services.workflow import run_workflow_with_progress
    from app.services.workflow_run_cancel import clear_run, register_run

    conversation_api_key = aios.get("conversation_api_key")
    results: list[dict[str, Any]] = []
    for wf in workflows:
        cancel_event = register_run(workspace_id, user_id)
        try:
            result = await run_workflow_with_progress(
                db,
                wf,
                user_id,
                aios.get("goal") or "Run from chat",
                None,
                workspace_id,
                conversation_api_key=conversation_api_key,
                cancel_event=cancel_event,
            )
            status = result.get("status") or "completed"
            results.append(
                {
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "status": status,
                    "output": (result.get("output") or "")[:400],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "status": "error",
                    "output": str(exc)[:200],
                }
            )
        finally:
            clear_run(workspace_id, user_id)
    aios["parallel_runs"] = results
    _save_aios(db, conv, aios)
    summary = "; ".join(f"{r['workflow_name']}: {r['status']}" for r in results)
    return {
        "events": [
            {
                "type": "aios_run_status",
                "data": {
                    "status": "completed",
                    "parallel": True,
                    "results": results,
                    "message": summary,
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Parallel run: {summary}",
    }


async def delete_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, text, aios)
    if not wf:
        return {
            "events": [{"type": "aios_run_status", "data": {"status": "error", "message": "No workflow found to delete."}}],
            "blocked_normal_reply": False,
            "summary": "No workflow found to delete.",
        }
    wf_name = wf.name
    try:
        db.delete(wf)
        db.commit()
    except Exception:
        pass
    aios["deleted_workflow"] = wf_name
    _save_aios(db, conv, aios)
    return {
        "events": [{"type": "aios_run_status", "data": {"status": "deleted", "message": f"Deleted workflow '{wf_name}'."}}],
        "blocked_normal_reply": False,
        "summary": f"Workflow '{wf_name}' has been deleted from disk successfully.",
    }


async def clone_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, text, aios)
    if not wf:
        return {
            "events": [{"type": "aios_run_status", "data": {"status": "error", "message": "No workflow found to clone."}}],
            "blocked_normal_reply": True,
            "summary": "No workflow found to clone.",
        }
    clone = Workflow(
        name=f"{wf.name} (copy)",
        desc=wf.desc,
        graph_json=wf.graph_json,
        user_id=user_id,
        workspace_id=workspace_id,
        status=wf.status,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    aios["last_workflow_id"] = clone.id
    _save_aios(db, conv, aios)
    return {
        "events": [
            {
                "type": "aios_run_status",
                "data": {
                    "status": "cloned",
                    "workflow_id": clone.id,
                    "workflow_name": clone.name,
                    "message": f"Cloned workflow as '{clone.name}'.",
                    "links": {"workflow": f"/workflows/{clone.id}"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Cloned workflow **{clone.name}**.",
    }


async def update_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, text, aios)
    preview = aios.get("executable_preview") or {}
    if not wf:
        return {
            "events": [{"type": "aios_run_status", "data": {"status": "error", "message": "No workflow found to update."}}],
            "blocked_normal_reply": True,
            "summary": "No workflow found to update.",
        }
    if not preview.get("nodes"):
        return {
            "events": [
                {
                    "type": "aios_run_status",
                    "data": {
                        "status": "error",
                        "message": "No blueprint graph in chat — compose and approve first.",
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No blueprint to apply.",
        }
    wf.graph_json = json.dumps(
        {"nodes": preview.get("nodes") or [], "edges": preview.get("edges") or []}
    )
    db.commit()
    return {
        "events": [
            {
                "type": "aios_run_status",
                "data": {
                    "status": "updated",
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "message": f"Updated workflow '{wf.name}' from current blueprint.",
                    "links": {"workflow": f"/workflows/{wf.id}"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Updated workflow **{wf.name}** from blueprint.",
    }


def workflow_status_event(db: Session, workspace_id: int, conversation_id: str | None) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    _ = conv
    last = aios.get("last_run") or {}
    wf_id = last.get("workflow_id") or aios.get("last_workflow_id") or (aios.get("deploy") or {}).get("workflow_id")
    run = None
    if last.get("run_id"):
        run = db.get(WorkflowRun, last["run_id"])
    if not run and wf_id:
        run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.workflow_id == wf_id, WorkflowRun.workspace_id == workspace_id)
            .order_by(WorkflowRun.create_time.desc())
            .first()
        )
    if not run:
        return {
            "type": "aios_run_status",
            "data": {"status": "idle", "message": "No recent runs in this conversation."},
        }
    status_map = {1: "completed", 2: "failed"}
    st = status_map.get(int(run.status or 0), str(run.status))
    return {
        "type": "aios_run_status",
        "data": {
            "status": st,
            "workflow_id": run.workflow_id,
            "run_id": run.id,
            "output": (run.output_text or "")[:800],
            "links": {"workflow": f"/workflows/{run.workflow_id}"},
            "timeline": True,
        },
    }


def index_attachments(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    from app.database import ConversationAttachment
    from app.services.knowledge import process_file_records_bg

    if not conversation_id:
        return {
            "events": [
                {"type": "aios_knowledge", "data": {"status": "error", "message": "No conversation for attachments."}}
            ],
            "blocked_normal_reply": True,
            "summary": "Open a chat and attach files first.",
        }
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
        return {
            "events": [
                {
                    "type": "aios_knowledge",
                    "data": {"status": "error", "message": "No attachments to index. Attach files first."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No attachments found.",
        }
    kb = KnowledgeBase(
        name=f"Chat KB {str(conversation_id)[:8]}",
        description="Indexed from chat attachments",
        user_id=user_id,
        workspace_id=workspace_id,
        type=0,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    files: list[KnowledgeFile] = []
    for r in rows[:12]:
        files.append(
            KnowledgeFile(
                knowledge_id=kb.id,
                file_name=r.file_name or "attachment",
                file_path=r.storage_key or "",
                status=5,
            )
        )
    db.add_all(files)
    db.commit()
    record_ids = [fr.id for fr in files]
    # Background indexing — avoids blocking chat on GB-scale files
    try:
        t = threading.Thread(
            target=process_file_records_bg,
            args=(record_ids, 1000, 100),
            daemon=True,
        )
        t.start()
    except Exception as exc:  # noqa: BLE001
        logger.warning("bg index start failed, falling back sync: %s", exc)
        for fr in files:
            try:
                process_file_record(db, fr, chunk_size=1000, chunk_overlap=100)
            except Exception as e2:  # noqa: BLE001
                logger.warning("index attachment failed: %s", e2)
    conv, aios = _load_aios(db, conversation_id)
    aios["knowledge_id"] = kb.id
    aios["indexing_status"] = "indexing"
    aios["memory_hints"] = list(
        dict.fromkeys((aios.get("memory_hints") or []) + [f"knowledge:{kb.id}"])
    )
    _save_aios(db, conv, aios)
    audit_chat_action(
        db,
        action="index_attachment",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="knowledge",
        resource_id=str(kb.id),
    )
    return {
        "events": [
            {
                "type": "aios_knowledge",
                "data": {
                    "status": "indexing",
                    "knowledge_id": kb.id,
                    "file_count": len(files),
                    "message": (
                        f"Indexing {len(files)} file(s) into Knowledge `{kb.id}` in the background. "
                        "You can keep chatting — say **use knowledge** when ready."
                    ),
                    "chips": ["Use knowledge", "Build a weekly email digest from my documents"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Started indexing {len(files)} attachment(s) into Knowledge `{kb.id}`.",
    }


def store_chat_knowledge_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.database import KnowledgeChunk
    from app.services.knowledge import chunk_text

    conv = db.get(Conversation, conversation_id) if conversation_id else None
    body = (text or "").strip()
    if conv and len(body) < 80:
        try:
            meta = json.loads(conv.meta_json or "{}")
            turns = meta.get("messages") or meta.get("turns") or []
            if isinstance(turns, list) and turns:
                parts = []
                for turn in turns[-12:]:
                    if isinstance(turn, dict):
                        parts.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
                    else:
                        parts.append(str(turn))
                body = "\n".join(parts).strip() or body
        except json.JSONDecodeError:
            pass
    if not body:
        return {
            "events": [
                {
                    "type": "aios_knowledge",
                    "data": {"status": "error", "message": "Nothing to store — chat first or paste text."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No content to store.",
        }

    kb = KnowledgeBase(
        name=f"Chat notes {str(conversation_id or 'session')[:8]}",
        description="Stored from chat",
        user_id=user_id,
        workspace_id=workspace_id,
        type=0,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    kf = KnowledgeFile(
        knowledge_id=kb.id,
        file_name="chat_notes.txt",
        file_path="chat://notes",
        status=5,
    )
    db.add(kf)
    db.commit()
    db.refresh(kf)
    pieces = chunk_text(body, 1000, 100)
    for i, piece in enumerate(pieces):
        db.add(KnowledgeChunk(knowledge_id=kb.id, file_id=kf.id, chunk_index=i, text=piece))
    db.commit()

    conv_row, aios = _load_aios(db, conversation_id)
    aios["knowledge_id"] = kb.id
    _save_aios(db, conv_row, aios)
    return {
        "events": [
            {
                "type": "aios_knowledge",
                "data": {
                    "status": "stored",
                    "knowledge_id": kb.id,
                    "name": kb.name,
                    "message": f"Stored in knowledge **{kb.name}** ({len(pieces)} chunks).",
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Stored in knowledge **{kb.name}**.",
    }


def list_llm_providers_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    from app.composer.llm_resolve import list_llm_alternatives, resolve_chat_llm_config

    _, aios = _load_aios(db, conversation_id)
    cfg = resolve_chat_llm_config(db, workspace_id, user_id, aios)
    alts = cfg.get("available_alternatives") or list_llm_alternatives(db, workspace_id, user_id, aios)
    msg = f"Active: {cfg.get('planning_label') or cfg.get('provider_name')}"
    return {
        "events": [
            {
                "type": "aios_meta",
                "data": {
                    "message": msg,
                    "planning_label": cfg.get("planning_label"),
                    "planning_source": cfg.get("source"),
                    "providers": alts,
                    "chips": ["Switch model", "Use workspace default"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": msg,
    }


def switch_planning_model_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.composer.llm_resolve import apply_planning_model_switch, resolve_chat_llm_config

    conv, aios = _load_aios(db, conversation_id)
    if not apply_planning_model_switch(aios, text, db, workspace_id, user_id):
        return {
            "events": [{"type": "aios_error", "data": {"message": "Say e.g. use model openai/gpt-4o-mini"}}],
            "blocked_normal_reply": True,
            "summary": "Could not parse model.",
        }
    _save_aios(db, conv, aios)
    cfg = resolve_chat_llm_config(db, workspace_id, user_id, aios)
    return {
        "events": [
            {
                "type": "aios_meta",
                "data": {
                    "message": f"Planning: **{cfg.get('planning_label')}**",
                    "planning_label": cfg.get("planning_label"),
                    "chips": ["Yes build this", "List providers"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": cfg.get("planning_label") or "Model set",
    }


def use_workspace_llm_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    from app.composer.llm_resolve import resolve_chat_llm_config

    conv, aios = _load_aios(db, conversation_id)
    aios.pop("planning_override", None)
    aios.pop("planning_model", None)
    _save_aios(db, conv, aios)
    cfg = resolve_chat_llm_config(db, workspace_id, user_id, aios)
    return {
        "events": [
            {
                "type": "aios_meta",
                "data": {
                    "message": f"Using **{cfg.get('planning_label')}**",
                    "planning_label": cfg.get("planning_label"),
                    "chips": ["List providers", "Switch model"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": cfg.get("planning_label") or "Workspace LLM",
    }


async def create_component_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.services.dynamic_component_creator import ComponentDiscovery, DynamicComponentCreator
    from app.services.user_management import UserApiKeyManager

    mgr = UserApiKeyManager(db)
    api_key = mgr.get_user_api_key(user_id)
    discovery = ComponentDiscovery()
    creator = DynamicComponentCreator(discovery, api_key)
    m = re.search(
        r"(?:create|make|build|new)\s+component\s+[\"']?([a-zA-Z0-9_\- ]{2,60})",
        text or "",
        re.I,
    )
    name = (m.group(1).strip().replace(" ", "_") if m else "custom_component")
    purpose = text or name
    result = await creator.create_component_if_missing(name, purpose)
    status = result.get("status") or "error"
    msg = result.get("message") or f"Component {name}: {status}"
    return {
        "events": [
            {
                "type": "aios_forge",
                "data": {
                    "message": msg,
                    "component": (result.get("component") or {}).get("name") or name,
                    "status": status,
                    "chips": ["Build a workflow for this", "Show forge", "What can you do?"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": msg,
    }


def requirements_confirm_action(db: Session, *, conversation_id: str | None) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    aios["requirements_confirmed"] = True
    pending = aios.get("pending_compose_goal") or ""
    _save_aios(db, conv, aios)
    out: dict[str, Any] = {
        "events": [
            {
                "type": "aios_requirements_brief",
                "data": {"status": "confirmed", "message": "Confirmed — building workflow."},
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Building workflow.",
    }
    if pending:
        out["recompose_after_confirm"] = True
        out["recompose_goal"] = pending
    return out


def use_knowledge(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    m = re.search(r"(?:knowledge(?:\s+base)?|kb)\s*[#:]?\s*(\d+)", text or "", re.I)
    kid = int(m.group(1)) if m else aios.get("knowledge_id")
    if not kid:
        # latest KB in workspace
        kb = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.workspace_id == workspace_id)
            .order_by(KnowledgeBase.id.desc())
            .first()
        )
        kid = kb.id if kb else None
    if not kid:
        return {
            "events": [
                {
                    "type": "aios_knowledge",
                    "data": {"status": "error", "message": "No knowledge base found. Create one or index attachments."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No knowledge base available.",
        }
    kb = db.get(KnowledgeBase, kid)
    if not kb or int(kb.workspace_id or 0) != int(workspace_id):
        return {
            "events": [{"type": "aios_knowledge", "data": {"status": "error", "message": "Knowledge base not found."}}],
            "blocked_normal_reply": True,
            "summary": "Knowledge base not found.",
        }
    aios["knowledge_id"] = kid
    _save_aios(db, conv, aios)
    return {
        "events": [
            {
                "type": "aios_knowledge",
                "data": {
                    "status": "linked",
                    "knowledge_id": kid,
                    "name": kb.name,
                    "message": f"Linked knowledge `{kb.name}` ({kid}) to this chat plan.",
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Using knowledge **{kb.name}** (`{kid}`).",
    }


def credentials_needed_event(aios: dict[str, Any]) -> dict[str, Any]:
    from app.composer.chat_requirements import oauth_assist_url

    missing = aios.get("missing_credentials") or []
    req = aios.get("requirements") or {}
    oauth_url = oauth_assist_url(req.get("integration"))
    return {
        "type": "aios_credentials_needed",
        "data": {
            "missing": missing or ["No gaps recorded — open Credentials to manage vault entries"],
            "credentials_url": oauth_url,
            "oauth_assist_url": oauth_url,
            "chips": ["Open credentials", "What credentials?"],
        },
    }


async def dispatch_ops_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    intent: str | None = None,
    workspace_role: str | None = "editor",
) -> dict[str, Any] | None:
    """Handle ops intents. Returns None if not an ops intent."""
    intent = intent or classify_ops_intent(user_message)
    if not intent or intent not in OPS_INTENTS:
        return None

    from app.composer import chat_enterprise as ent

    denied = ent.gate_role(workspace_role, intent)
    if denied:
        return denied

    # Workspace enforce policies (PlatformPolicy)
    from app.composer.chat_requirements import check_chat_policy

    if intent in ("run_workflow", "run_workflows_parallel", "test_workflow", "schedule_create", "schedule_pause", "fulfill_requirements", "test_notification", "incident_kill_switch"):
        policy_block = check_chat_policy(db, workspace_id=workspace_id, action=intent)
        if policy_block:
            return policy_block

    if intent == "capabilities":
        ev = capabilities_event()
        return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["title"]}

    if intent == "list_workflows":
        ev = list_workflows_event(db, workspace_id)
        names = ", ".join(w["name"] for w in (ev["data"].get("workflows") or [])[:8]) or "none"
        return {
            "events": [ev],
            "blocked_normal_reply": True,
            "summary": f"Workflows ({ev['data']['count']}): {names}",
        }

    if intent == "run_workflow":
        if not check_compose_rate(workspace_id, user_id):
            return {
                "events": [
                    {
                        "type": "aios_run_status",
                        "data": {"status": "error", "message": "Rate limit — try again in a minute."},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Too many chat actions — wait a moment.",
            }
        return await run_workflow_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "run_workflows_parallel":
        if not check_compose_rate(workspace_id, user_id):
            return {
                "events": [
                    {
                        "type": "aios_run_status",
                        "data": {"status": "error", "message": "Rate limit — try again in a minute."},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Too many chat actions — wait a moment.",
            }
        return await run_workflows_parallel_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "test_workflow":
        return await test_workflow_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "delete_workflow":
        return await delete_workflow_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "clone_workflow":
        return await clone_workflow_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "update_workflow":
        return await update_workflow_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "workflow_status" or intent == "monitor":
        ev = workflow_status_event(db, workspace_id, conversation_id)
        return {
            "events": [ev],
            "blocked_normal_reply": True,
            "summary": f"Run status: {ev['data'].get('status')}",
        }

    if intent == "stop_run":
        from app.services.workflow_run_cancel import request_cancel

        conv, aios = _load_aios(db, conversation_id)
        cancelled = request_cancel(workspace_id, user_id)
        aios["stop_requested"] = True
        aios["status"] = aios.get("status") or "stopped"
        _save_aios(db, conv, aios)
        return {
            "events": [
                {
                    "type": "aios_run_status",
                    "data": {
                        "status": "stopped",
                        "message": (
                            "Run stop signalled — in-flight step will end shortly."
                            if cancelled
                            else "No active run found to stop."
                        ),
                        "run_id": aios.get("active_run_id"),
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Stop requested.",
        }

    if intent == "index_attachment":
        return index_attachments(
            db, workspace_id=workspace_id, user_id=user_id, conversation_id=conversation_id
        )

    if intent == "store_chat_knowledge":
        return store_chat_knowledge_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "list_llm_providers":
        return list_llm_providers_action(
            db, workspace_id=workspace_id, user_id=user_id, conversation_id=conversation_id
        )

    if intent == "switch_planning_model":
        return switch_planning_model_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "use_workspace_llm":
        return use_workspace_llm_action(
            db, workspace_id=workspace_id, user_id=user_id, conversation_id=conversation_id
        )

    if intent == "create_component":
        return await create_component_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "requirements_confirm":
        return requirements_confirm_action(db, conversation_id=conversation_id)

    if intent == "use_knowledge":
        return use_knowledge(db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message)

    if intent == "list_credentials_needed":
        # Prefer vault posture gaps event when asking "what credentials"
        if re.search(r"\bwhat credentials\b|\bmissing credentials\b", user_message or "", re.I):
            return ent.vault_action(
                db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
            )
        _, aios = _load_aios(db, conversation_id)
        ev = credentials_needed_event(aios)
        return {
            "events": [ev],
            "blocked_normal_reply": True,
            "summary": f"Missing: {', '.join(ev['data']['missing'])}",
        }

    if intent == "list_schedules":
        return ent.list_schedules_action(db, workspace_id)

    if intent == "schedule_create":
        return ent.create_schedule_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "schedule_pause":
        return ent.pause_schedule_action(
            db, workspace_id=workspace_id, user_id=user_id, text=user_message
        )

    if intent == "compliance_report":
        return ent.compliance_action(db, workspace_id, user_message)

    if intent == "finops_summary":
        return ent.finops_action(db, workspace_id)

    if intent == "workspace_health":
        return ent.health_action(db, workspace_id)

    if intent in ("list_recommendations", "approve_recommendation"):
        return ent.recommendations_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            text=user_message,
            intent=intent,
        )

    if intent == "export_conversation":
        return ent.export_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "share_conversation":
        return ent.share_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent in ("title_conversation", "tag_conversation", "summarize_conversation"):
        return await ent.meta_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
            intent=intent,
        )

    if intent == "audit_trail":
        return ent.audit_trail_action(
            db, workspace_id=workspace_id, user_id=user_id, text=user_message
        )

    if intent == "vault_posture":
        return ent.vault_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
        )

    if intent in ("integrations_health", "test_notification"):
        return await ent.integration_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            text=user_message,
            intent=intent,
        )

    if intent == "playbook":
        return ent.playbook_action(user_message)

    if intent == "capture_requirements":
        from app.composer.chat_requirements import capture_requirements_action

        return capture_requirements_action(
            db,
            conversation_id=conversation_id,
            text=user_message,
            user_id=user_id,
            workspace_id=workspace_id,
        )

    if intent == "show_requirements":
        from app.composer.chat_requirements import show_requirements_action

        return show_requirements_action(db, conversation_id)

    if intent == "fulfill_requirements":
        from app.composer.chat_requirements import fulfill_requirements_action

        return fulfill_requirements_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )

    if intent == "show_policy":
        from app.database import PlatformPolicy

        rows = (
            db.query(PlatformPolicy)
            .filter(PlatformPolicy.workspace_id == workspace_id, PlatformPolicy.enabled == 1)
            .order_by(PlatformPolicy.id.desc())
            .limit(20)
            .all()
        )
        items = [
            {
                "rule_key": r.rule_key,
                "severity": r.severity,
                "value": (r.rule_value or "")[:120],
                "type": r.policy_type,
            }
            for r in rows
        ]
        return {
            "events": [
                {
                    "type": "aios_policy",
                    "data": {
                        "status": "list",
                        "title": "Workspace chat policies",
                        "policies": items,
                        "count": len(items),
                        "message": (
                            f"{len(items)} enforce/advisory policy row(s). "
                            "Empty list means default allow (RBAC still applies)."
                        ),
                        "chips": ["Workspace health", "Compliance report", "Show requirements"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": f"{len(items)} policy row(s).",
        }

    from app.composer.chat_autopilot import AUTOPILOT_INTENTS, dispatch_autopilot_action

    if intent in AUTOPILOT_INTENTS:
        return await dispatch_autopilot_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=intent,
            workspace_role=workspace_role,
        )

    from app.composer.chat_forge import FORGE_INTENTS, dispatch_forge_action

    if intent in FORGE_INTENTS:
        return await dispatch_forge_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=intent,
        )

    from app.composer.chat_powerhouse import POWER_INTENTS, dispatch_power_action

    if intent in POWER_INTENTS:
        return await dispatch_power_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=intent,
        )

    from app.composer.chat_node_factory import (
        NAV_INTENTS,
        NODE_FACTORY_INTENTS,
        dispatch_nav_action,
        dispatch_node_factory_action,
    )

    if intent in NODE_FACTORY_INTENTS:
        return await dispatch_node_factory_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=intent,
        )

    if intent in NAV_INTENTS:
        return dispatch_nav_action(intent, user_message)

    return None
