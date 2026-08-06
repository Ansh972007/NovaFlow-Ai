"""Enterprise requirements capture + fulfillment checklist for Peak Chat."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.composer.chat_router import infer_field


def parse_requirements(text: str, *, last_field: str | None = None, db: Session | None = None) -> dict[str, Any]:
    """Extract a structured requirements brief from free text (heuristic)."""
    t = (text or "").strip()
    g = t.lower()
    field = infer_field(t, last_field)

    trigger = "manual"
    if re.search(r"\b(every|daily|weekly|monday|cron|schedule)\b", g):
        trigger = "schedule"
    elif re.search(r"\b(webhook|http|api call)\b", g):
        trigger = "webhook"
    elif re.search(r"\b(telegram|slack|discord)\s+bot\b|\bfrom chat\b", g):
        trigger = "chat"

    data = "none"
    if re.search(r"\b(knowledge|docs|documents|from my|policy|rag)\b", g):
        data = "knowledge"
    elif re.search(r"\b(upload|attachment|csv|file)\b", g):
        data = "upload"
    elif re.search(r"\b(api|webhook|http)\b", g):
        data = "api"
    elif re.search(r"\b(any subject|various topics|different topics|dynamic content)\b", g):
        data = "dynamic_llm"

    output = "workflow"
    integration = None
    if re.search(r"\byoutube\b|\byt\s+channel\b", g):
        integration = "youtube"
    elif re.search(r"\bgoogle\s+drive\b|\bgdrive\b|\bonedrive\b", g):
        integration = "google_drive" if "onedrive" not in g else "onedrive"
    elif re.search(r"\bgoogle\s+sheets\b|\bspreadsheet\b|\bexcel\b", g):
        integration = "google_sheets"
    elif re.search(r"\bgoogle\s+calendar\b|\bgcal\b", g):
        integration = "google_calendar"
    elif re.search(r"\boutlook\s+calendar\b|\bmicrosoft\s+calendar\b", g):
        integration = "outlook_calendar"
    elif re.search(r"\bgoogle\b", g) and re.search(r"\b(drive|sheet|calendar|api)\b", g):
        integration = "google_api"
    elif re.search(r"\boutlook\b|\bmicrosoft\s+365\b|\boffice\s+365\b", g):
        integration = "outlook_mail"

    explicit_email = bool(
        re.search(r"\b(send|emails?|smtp|mail|welcome email|reminder)\b", g)
        and not re.search(r"\b(send\s+to\s+chat|in\s+chat)\b", g)
    )
    if integration == "youtube" and not explicit_email:
        output = "youtube"
    elif re.search(r"\b(emails?|smtp|mail|welcome email|reminder)\b", g) or re.search(
        r"\bsend\s+\d+\s+emails?\b", g
    ):
        output = "email"
    elif re.search(r"\bslack\b", g):
        output = "slack"
    elif re.search(r"\btelegram\b", g):
        output = "telegram"
    elif re.search(r"\bdiscord\b", g):
        output = "discord"
    elif re.search(r"\b(github|jira|linear)\b", g):
        output = "ticket"
    elif integration in ("google_sheets", "google_drive", "google_calendar", "google_api"):
        output = integration
    elif integration == "youtube":
        output = "youtube"

    needs_approval = bool(
        re.search(r"\b(approve|approval|ask me|hitl|human)\b", g)
    )
    sla = None
    sm = re.search(r"\b(sla|within)\s+(\d+)\s*(h|hours?|m|minutes?|d|days?)\b", g)
    if sm:
        sla = f"{sm.group(2)}{sm.group(3)[0]}"

    # Extract email recipient if mentioned
    email_recipient = None
    email_match = re.search(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', t)
    if email_match:
        email_recipient = email_match.group(1)

    recipients: list[str] = []
    if email_recipient:
        recipients.append(email_recipient)
    for addr in re.findall(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', t):
        if addr not in recipients:
            recipients.append(addr)
    if re.search(r"\bmy friends\b|\bfriends\b|\bcolleagues\b|\bteam members\b", g):
        recipients_label = "friends"
    elif recipients:
        recipients_label = ", ".join(recipients[:5])
    else:
        recipients_label = None

    email_topic = None
    if output == "email":
        topic_m = re.search(
            r"\b(?:on|about|regarding|for|topic)\s+(?:the\s+)?([a-zA-Z][a-zA-Z0-9\s\-]{2,40}?)(?:\s+topic)?(?:\s+to|\s+for|\s+with|\s+using|$|[.,!])",
            t,
            re.I,
        )
        if topic_m and not re.search(r"\byoutube\b", topic_m.group(1), re.I):
            email_topic = topic_m.group(1).strip()
        elif re.search(r"\bdiwali\b", g):
            email_topic = "Diwali"

    email_count = None
    if output == "email":
        count_m = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+emails?\b", g)
        if count_m:
            word = count_m.group(1)
            word_map = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            }
            email_count = int(word) if word.isdigit() else word_map.get(word, None)

    auth_preference = None
    if re.search(r"\b(google oauth|google auth|gmail oauth|oauth)\b", g):
        auth_preference = "google_oauth"
    elif re.search(r"\b(smtp|app password|gmail smtp)\b", g):
        auth_preference = "smtp"
    elif re.search(r"\bgoogle\b|\bgmail\b", g) and output == "email":
        auth_preference = "google_oauth"

    workflow_name = None
    name_m = re.search(r"\bname (it|this|the workflow)\s+(.+)$", t, re.I)
    if name_m:
        workflow_name = name_m.group(2).strip().strip('"\'')

    # Extract sender email if mentioned
    email_sender = None
    sender_match = re.search(r'\b(my gmail|my email|sender is|from)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', t, re.IGNORECASE)
    if sender_match:
        email_sender = sender_match.group(2)

    # Check if user has API key configured
    has_api_key = False
    if db is not None:
        try:
            from app.services.llm_providers import get_active_provider_row
            from app.crypto import decrypt_secret
            
            provider_row = get_active_provider_row(db)
            if provider_row:
                api_key = decrypt_secret(provider_row.api_key_enc or "")
                if api_key:
                    has_api_key = True
        except Exception:
            has_api_key = False

    checklist = [
        {"id": "goal", "label": "Business goal captured", "done": bool(t)},
        {"id": "field", "label": f"Field: {field}", "done": field != "generic" or len(t) > 40},
        {"id": "trigger", "label": f"Trigger: {trigger}", "done": True},
        {"id": "data", "label": f"Data: {data}", "done": data != "none" or "generic" in field},
        {"id": "output", "label": f"Output: {output}", "done": True},
        {"id": "api_key", "label": "User API key configured", "done": has_api_key},
        {"id": "creds", "label": "Service credentials configured", "done": bool(email_sender)},
        {"id": "plan", "label": "Workflow plan composed", "done": False},
        {"id": "approve", "label": "Plan approved", "done": False},
        {"id": "test", "label": "Sandbox tested", "done": False},
        {"id": "deploy", "label": "Deployed", "done": False},
    ]
    if needs_approval:
        checklist.insert(
            6,
            {"id": "hitl", "label": "Human approval required before side-effects", "done": False},
        )

    return {
        "id": uuid.uuid4().hex[:16],
        "raw": t[:2000],
        "goal": t[:1000],
        "field": field,
        "trigger": trigger,
        "data": data,
        "output": output,
        "needs_approval": needs_approval,
        "sla": sla,
        "email_recipient": email_recipient,
        "email_sender": email_sender,
        "email_topic": email_topic,
        "email_count": email_count,
        "recipients": recipients,
        "recipients_label": recipients_label,
        "auth_preference": auth_preference,
        "workflow_name": workflow_name,
        "integration": integration,
        "has_api_key": has_api_key,
        "checklist": checklist,
        "status": "captured",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def requirements_event(req: dict[str, Any], *, message: str = "") -> dict[str, Any]:
    done = sum(1 for c in (req.get("checklist") or []) if c.get("done"))
    total = len(req.get("checklist") or []) or 1
    
    # Check if this is a dynamic email request
    is_dynamic_email = req.get("data") == "dynamic_llm" and req.get("output") == "email"
    
    # Check if user needs to add API key
    needs_api_key = not req.get("has_api_key", False)
    
    # Customize message based on missing API key
    if needs_api_key:
        message = "To build workflows with AI features, you'll need to add your API key first. Please go to **Settings → Model providers** to add your OpenRouter, OpenAI, or other provider API key."
    
    # Customize chips based on requirements
    chips = [
        "Fulfill these requirements",
        "Show requirements",
        "What credentials are missing?",
        "Enterprise playbooks",
    ]
    
    if needs_api_key:
        chips = [
            "Add API key in Settings",
            "Show requirements",
            "Continue without AI",
        ]
    
    return {
        "type": "aios_requirements",
        "data": {
            "title": "Requirements brief",
            "message": message or "Captured enterprise requirements for this ask.",
            "requirement": req,
            "progress": f"{done}/{total}",
            "is_dynamic_email": is_dynamic_email,
            "email_recipient": req.get("email_recipient"),
            "email_sender": req.get("email_sender"),
            "needs_api_key": needs_api_key,
            "chips": chips,
        },
    }


def fulfillment_event(req: dict[str, Any], *, message: str = "", solution: dict | None = None) -> dict[str, Any]:
    checklist = list(req.get("checklist") or [])
    done = sum(1 for c in checklist if c.get("done"))
    
    # Customize for dynamic email requests
    is_dynamic_email = req.get("data") == "dynamic_llm" and req.get("output") == "email"
    needs_api_key = not req.get("has_api_key", False)
    
    chips = ["approve", "run test", "deploy", "Show requirements"]
    
    if is_dynamic_email:
        chips = [
            "Build dynamic email workflow",
            "Test with sample content",
            "Deploy for use",
            "Show requirements"
        ]
    
    if needs_api_key:
        chips = [
            "Add API key in Settings",
            "Show requirements",
            "Continue without AI"
        ]
    
    # Customize message for missing API key
    if needs_api_key and not message:
        message = "To use AI features in this workflow, please add your API key in Settings → Model providers."
    
    return {
        "type": "aios_fulfillment",
        "data": {
            "title": "Fulfillment progress",
            "message": message or "Working the requirements checklist.",
            "requirement_id": req.get("id"),
            "field": req.get("field"),
            "checklist": checklist,
            "progress": f"{done}/{len(checklist) or 1}",
            "solution_id": (solution or {}).get("solution_id"),
            "is_dynamic_email": is_dynamic_email,
            "email_recipient": req.get("email_recipient"),
            "email_sender": req.get("email_sender"),
            "needs_api_key": needs_api_key,
            "chips": chips,
        },
    }


def mark_checklist(req: dict[str, Any], item_id: str, done: bool = True) -> dict[str, Any]:
    for c in req.get("checklist") or []:
        if c.get("id") == item_id:
            c["done"] = done
    return req


def sync_checklist_from_aios(req: dict[str, Any], aios: dict[str, Any]) -> dict[str, Any]:
    """Update checklist from conversation AIOS state."""
    if aios.get("solution_id"):
        mark_checklist(req, "plan", True)
    if aios.get("missing_credentials") is not None:
        mark_checklist(req, "creds", not bool(aios.get("missing_credentials")))
    if aios.get("approved"):
        mark_checklist(req, "approve", True)
    if aios.get("tested"):
        mark_checklist(req, "test", True)
    if (aios.get("status") or "") in ("deployed", "done"):
        mark_checklist(req, "deploy", True)
    if aios.get("solution_id"):
        req["status"] = "in_progress"
    if (aios.get("status") or "") in ("deployed", "done"):
        req["status"] = "fulfilled"
    return req


def compose_goal_from_requirements(req: dict[str, Any]) -> str:
    trigger_label = req.get("trigger") or "manual"
    if trigger_label == "schedule":
        trigger_label = "scheduled"
    parts = [
        req.get("goal") or req.get("raw") or "Automate this work",
        f"Field: {req.get('field')}.",
        f"Run cadence: {trigger_label}.",
        f"Data source: {req.get('data')}.",
        f"Output channel: {req.get('output')}.",
    ]
    if req.get("integration"):
        parts.append(f"Primary integration: {req['integration']}.")
    if req.get("email_topic"):
        parts.append(f"Email topic: {req['email_topic']}.")
    if req.get("email_count"):
        parts.append(f"Send {req['email_count']} emails.")
    if req.get("recipients_label"):
        parts.append(f"Recipients: {req['recipients_label']}.")
    elif req.get("recipients"):
        parts.append(f"Recipients: {', '.join(req['recipients'][:5])}.")
    elif req.get("email_recipient"):
        parts.append(f"Recipient: {req['email_recipient']}.")
    if req.get("auth_preference"):
        parts.append(f"Auth: {req['auth_preference']}.")
    if req.get("needs_approval"):
        parts.append("Ask me before acting (HITL).")
    if req.get("sla"):
        parts.append(f"SLA target: {req['sla']}.")
    return " ".join(parts)


def merge_requirements_from_message(req: dict[str, Any], text: str, *, db: Session | None = None) -> dict[str, Any]:
    """Merge follow-up user details into stored requirements."""
    merged = dict(req or {})
    fresh = parse_requirements(text, last_field=merged.get("last_field"), db=db)
    for key in (
        "goal", "raw", "field", "trigger", "data", "output",
        "email_recipient", "email_sender",         "email_topic", "email_count",
        "recipients_label", "auth_preference", "workflow_name", "integration", "sla",
        "needs_approval", "has_api_key",
    ):
        val = fresh.get(key)
        if val is not None and val != "" and val is not False:
            merged[key] = val
    if fresh.get("recipients"):
        existing = list(merged.get("recipients") or [])
        for r in fresh["recipients"]:
            if r not in existing:
                existing.append(r)
        merged["recipients"] = existing
    if not merged.get("goal") and text.strip():
        merged["goal"] = text.strip()[:1000]
    g = (text or "").lower()
    if re.search(r"\buse\s+google\s+oauth\b|\bgoogle\s+oauth\b", g):
        merged["auth_preference"] = "google_oauth"
    if re.search(r"\buse\s+smtp\b|\bsmtp\b", g) and "oauth" not in g:
        merged["auth_preference"] = "smtp"
    merged["checklist"] = merged.get("checklist") or fresh.get("checklist") or []
    return merged


def missing_workflow_slots(req: dict[str, Any]) -> list[dict[str, str]]:
    """Return unfilled critical slots for workflow compose."""
    output = (req.get("output") or "").lower()
    missing: list[dict[str, str]] = []
    if output == "email":
        if not req.get("email_topic") and not re.search(
            r"\b(different|various|multiple)\s+(subjects?|topics?)\b",
            (req.get("goal") or req.get("raw") or "").lower(),
        ):
            missing.append({"id": "email_topic", "label": "Email topic or theme (e.g. Diwali)"})
        if not req.get("recipients_label") and not req.get("recipients") and not req.get("email_recipient"):
            missing.append({"id": "recipients", "label": "Who should receive the emails?"})
        if not req.get("auth_preference"):
            missing.append({"id": "auth_preference", "label": "Send via Google OAuth or SMTP?"})
    if not req.get("goal") and not req.get("raw"):
        missing.append({"id": "goal", "label": "What should this workflow do?"})
    return missing


def gather_prompt(
    req: dict[str, Any],
    missing_slots: list[dict[str, str]],
    missing_creds: list[str],
) -> str:
    """One professional question block for blueprint phase."""
    from app.composer.chat_channels import friendly_missing_name, paste_hints_for_missing

    lines = ["We'll build a **workflow** for this — review the blueprint below."]
    if missing_slots:
        lines.append("")
        lines.append("**Still needed:**")
        for slot in missing_slots[:4]:
            lines.append(f"- {slot['label']}")
    if missing_creds:
        lines.append("")
        if not missing_slots:
            lines.append("**Credentials needed** — paste secrets here or open Credentials:")
        else:
            lines.append("**After the above, credentials:**")
        for cred in missing_creds[:5]:
            lines.append(f"- {friendly_missing_name(cred)}")
        hints = paste_hints_for_missing(missing_creds)
        if hints:
            lines.append("")
            lines.append(f"Hint: {hints[0]}")
    if not missing_slots and not missing_creds:
        lines.append("")
        lines.append("Everything looks ready — tap **Approve** to build and test the workflow.")
    return "\n".join(lines)


def build_blueprint_preview(
    goal: str,
    req: dict[str, Any],
    caps: list[str],
    preview_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Human-readable blueprint steps + slot table for chat UI."""
    output = (req.get("output") or "workflow").lower()
    integration = (req.get("integration") or "").lower()
    topic = (req.get("email_topic") or req.get("goal") or goal or "your request")[:80]

    integration_steps: dict[str, list[str]] = {
        "youtube": [
            "Trigger workflow (manual or scheduled)",
            "Call YouTube Data API for channel / video stats",
            f"Analyze and summarize: {topic}",
            "Show results in chat",
        ],
        "google_sheets": [
            "Trigger on schedule or manual run",
            "Read or update Google Sheets via API",
            f"Process data for: {topic}",
            "Return sheet summary in chat",
        ],
        "google_drive": [
            "Trigger workflow",
            "List or sync files from Google Drive",
            f"Process content for: {topic}",
            "Return results in chat",
        ],
        "google_calendar": [
            "Trigger on schedule",
            "Fetch or create Google Calendar events",
            f"Handle calendar task: {topic}",
            "Confirm results in chat",
        ],
        "telegram": [
            "Receive message via Telegram bot trigger",
            "Process user request with AI",
            f"Reply on Telegram about: {topic}",
            "Log outcome in chat",
        ],
    }

    steps = integration_steps.get(integration) or integration_steps.get(output) or [
        "Capture trigger and inputs",
        "Prepare message content from your requirements",
        f"Deliver via {output}",
        "Return results to chat",
    ]
    if output == "email":
        count = req.get("email_count") or 1
        topic = req.get("email_topic") or "your topic"
        steps = [
            f"Trigger workflow (manual or scheduled)",
            f"Generate {count} email(s) about {topic}",
            "Send via email connector with your credentials",
            "Show send results in chat",
        ]

    slots: list[dict[str, Any]] = []
    slot_defs = [
        ("goal", "Goal", req.get("goal") or req.get("raw")),
        ("email_topic", "Topic", req.get("email_topic")),
        ("email_count", "Email count", req.get("email_count")),
        ("recipients", "Recipients", req.get("recipients_label") or (
            ", ".join(req.get("recipients") or []) if req.get("recipients") else req.get("email_recipient")
        )),
        ("auth_preference", "Auth method", req.get("auth_preference")),
        ("integration", "Integration", req.get("integration")),
        ("trigger", "Trigger", req.get("trigger")),
    ]
    for sid, label, val in slot_defs:
        if val is None or val == "":
            slots.append({"id": sid, "label": label, "value": None, "filled": False})
        else:
            slots.append({"id": sid, "label": label, "value": str(val), "filled": True})

    nodes = (preview_graph or {}).get("nodes") or []
    edges = (preview_graph or {}).get("edges") or []
    return {
        "steps": steps,
        "slots": slots,
        "preview_nodes": nodes,
        "preview_edges": edges,
        "capabilities": caps,
    }


def check_chat_policy(
    db: Session,
    *,
    workspace_id: int,
    action: str,
) -> dict[str, Any] | None:
    """
    Return aios_policy denial payload if an enforce policy blocks the action.
    action examples: run_workflow, schedule_create, deploy, fulfill_requirements
    """
    from app.database import PlatformPolicy

    try:
        rows = (
            db.query(PlatformPolicy)
            .filter(
                PlatformPolicy.workspace_id == workspace_id,
                PlatformPolicy.enabled == 1,
                PlatformPolicy.severity == "enforce",
            )
            .all()
        )
    except Exception:
        return None
    if not rows:
        return None

    blocked_keys = {
        "run_workflow": ("chat.block_run", "chat.freeze_runs"),
        "schedule_create": ("chat.block_schedule", "chat.freeze_runs"),
        "deploy": ("chat.block_deploy", "chat.change_freeze"),
        "fulfill_requirements": ("chat.block_compose", "chat.change_freeze"),
        "schedule_pause": ("chat.block_schedule",),
        "test_notification": ("chat.block_notify",),
    }
    keys = blocked_keys.get(action) or ()
    for row in rows:
        rk = (row.rule_key or "").strip().lower()
        if rk in keys or (rk == "chat.deny_all" and action != "capabilities"):
            return {
                "events": [
                    {
                        "type": "aios_policy",
                        "data": {
                            "status": "denied",
                            "action": action,
                            "rule_key": row.rule_key,
                            "severity": row.severity,
                            "message": (
                                f"Workspace policy `{row.rule_key}` blocks `{action}`. "
                                f"{(row.rule_value or '')[:200]}"
                            ).strip(),
                            "chips": ["Workspace health", "Show requirements", "Compliance report"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": f"Policy blocked: {row.rule_key}",
            }
    return None


def capture_requirements_action(
    db: Session,
    *,
    conversation_id: str | None,
    text: str,
    user_id: int,
    workspace_id: int,
) -> dict[str, Any]:
    from app.composer.chat_actions import _load_aios, _save_aios, audit_chat_action

    conv, aios = _load_aios(db, conversation_id)
    # Strip leading capture phrases
    body = re.sub(
        r"^\s*(capture|record|save|log)\s+(my\s+)?requirements?\s*(:|-)?\s*",
        "",
        text or "",
        flags=re.I,
    ).strip() or (text or "").strip()
    body = re.sub(r"^\s*requirements?\s*(:|-)\s*", "", body, flags=re.I).strip() or body
    req = parse_requirements(body, last_field=aios.get("last_field"), db=db)
    aios["requirements"] = req
    aios["last_field"] = req.get("field")
    _save_aios(db, conv, aios)
    audit_chat_action(
        db,
        action="capture_requirements",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="requirements",
        resource_id=str(req.get("id") or ""),
        detail={"field": req.get("field")},
    )
    ev = requirements_event(req)
    return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["message"]}


def show_requirements_action(db: Session, conversation_id: str | None) -> dict[str, Any]:
    from app.composer.chat_actions import _load_aios

    _, aios = _load_aios(db, conversation_id)
    req = aios.get("requirements")
    if not req:
        return {
            "events": [
                {
                    "type": "aios_requirements",
                    "data": {
                        "title": "No requirements yet",
                        "message": "Say **capture requirements:** then your ask, or describe the work to fulfill.",
                        "chips": [
                            "Capture requirements: onboard new hires with welcome email",
                            "Automate invoice reminders from my documents every Monday",
                        ],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No requirements captured yet.",
        }
    req = sync_checklist_from_aios(dict(req), aios)
    ev = requirements_event(req, message="Current requirements for this conversation.")
    return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["message"]}


def fulfill_requirements_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str = "",
) -> dict[str, Any]:
    """Compose a solution from stored (or inline) requirements."""
    from app.composer.chat_actions import _load_aios, _save_aios, audit_chat_action, check_compose_rate
    from app.composer.planner import compile_solution_blueprint
    from app.composer.recipes import progress_steps

    denied = check_chat_policy(db, workspace_id=workspace_id, action="fulfill_requirements")
    if denied:
        return denied

    if not check_compose_rate(workspace_id, user_id):
        return {
            "events": [
                {
                    "type": "aios_policy",
                    "data": {
                        "status": "rate_limited",
                        "message": "Rate limit — slow down fulfill/compose for a minute.",
                        "chips": ["Show requirements", "List my workflows"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Rate limited.",
        }

    conv, aios = _load_aios(db, conversation_id)
    req = aios.get("requirements")
    if not req or re.search(r"\bfulfill\b.+\bwith\b", text or "", re.I):
        # Inline: "fulfill requirements: ..."
        body = re.sub(r"^\s*fulfill(\s+these)?\s+requirements?\s*(:|-)?\s*", "", text or "", flags=re.I).strip()
        if body and body.lower() not in ("these requirements", "requirements", "this"):
            req = parse_requirements(body, last_field=aios.get("last_field"), db=db)
        elif not req:
            return show_requirements_action(db, conversation_id)

    goal = compose_goal_from_requirements(req)
    result = compile_solution_blueprint(db, workspace_id, goal)
    recipe_name = result.get("recipe_name") or (result.get("recipe") or {}).get("name")
    field = (result.get("recipe") or {}).get("field") or req.get("field")

    mark_checklist(req, "goal", True)
    mark_checklist(req, "field", True)
    mark_checklist(req, "plan", True)
    mark_checklist(req, "api_key", req.get("has_api_key", False))
    mark_checklist(req, "creds", not bool(result.get("missing_credentials")))
    req["status"] = "in_progress"

    aios.update(
        {
            "project_id": result.get("project_id"),
            "solution_id": result.get("solution_id"),
            "status": "pending_approval",
            "goal": goal,
            "mode": "workflow",
            "missing_credentials": result.get("missing_credentials") or [],
            "graph": result.get("graph") or {},
            "executable_preview": result.get("executable_preview") or {},
            "required_capabilities": result.get("required_capabilities") or [],
            "node_types": result.get("node_types") or [],
            "recipe": result.get("recipe"),
            "recipe_name": recipe_name,
            "progress": result.get("progress")
            or progress_steps(missing_credentials=result.get("missing_credentials")),
            "next_action": result.get("next_action") or "approve",
            "approved": False,
            "tested": False,
            "heal_count": 0,
            "last_recipe": recipe_name,
            "last_field": field,
            "requirements": req,
        }
    )
    _save_aios(db, conv, aios)
    audit_chat_action(
        db,
        action="fulfill_requirements",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="solution",
        resource_id=str(result.get("solution_id") or ""),
        detail={"requirement_id": req.get("id"), "field": field},
    )

    events = [
        requirements_event(req, message="Requirements locked — composing fulfillment plan."),
        {"type": "aios_solution", "data": {**aios, "status": "pending_approval"}},
        fulfillment_event(req, message="Checklist updated after compose.", solution=result),
    ]
    if result.get("missing_credentials"):
        events.append(
            {
                "type": "aios_credentials_needed",
                "data": {
                    "missing": result.get("missing_credentials"),
                    "credentials_url": "/credentials",
                },
            }
        )
    return {
        "events": events,
        "blocked_normal_reply": True,
        "summary": f"Fulfillment plan ready ({recipe_name or 'workflow'}). Approve to continue.",
    }
