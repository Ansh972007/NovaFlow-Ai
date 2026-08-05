"""Enterprise requirements capture + fulfillment checklist for Peak Chat."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.composer.chat_router import infer_field


def parse_requirements(text: str, *, last_field: str | None = None) -> dict[str, Any]:
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

    output = "workflow"
    if re.search(r"\b(email|smtp|mail|welcome email|reminder)\b", g):
        output = "email"
    elif re.search(r"\bslack\b", g):
        output = "slack"
    elif re.search(r"\btelegram\b", g):
        output = "telegram"
    elif re.search(r"\bdiscord\b", g):
        output = "discord"
    elif re.search(r"\b(github|jira|linear)\b", g):
        output = "ticket"

    needs_approval = bool(
        re.search(r"\b(approve|approval|ask me|hitl|human)\b", g)
    )
    sla = None
    sm = re.search(r"\b(sla|within)\s+(\d+)\s*(h|hours?|m|minutes?|d|days?)\b", g)
    if sm:
        sla = f"{sm.group(2)}{sm.group(3)[0]}"

    checklist = [
        {"id": "goal", "label": "Business goal captured", "done": bool(t)},
        {"id": "field", "label": f"Field: {field}", "done": field != "generic" or len(t) > 40},
        {"id": "trigger", "label": f"Trigger: {trigger}", "done": True},
        {"id": "data", "label": f"Data: {data}", "done": data != "none" or "generic" in field},
        {"id": "output", "label": f"Output: {output}", "done": True},
        {"id": "creds", "label": "Credentials / gaps checked", "done": False},
        {"id": "plan", "label": "Workflow plan composed", "done": False},
        {"id": "approve", "label": "Plan approved", "done": False},
        {"id": "test", "label": "Sandbox tested", "done": False},
        {"id": "deploy", "label": "Deployed", "done": False},
    ]
    if needs_approval:
        checklist.insert(
            5,
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
        "checklist": checklist,
        "status": "captured",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def requirements_event(req: dict[str, Any], *, message: str = "") -> dict[str, Any]:
    done = sum(1 for c in (req.get("checklist") or []) if c.get("done"))
    total = len(req.get("checklist") or []) or 1
    return {
        "type": "aios_requirements",
        "data": {
            "title": "Requirements brief",
            "message": message or "Captured enterprise requirements for this ask.",
            "requirement": req,
            "progress": f"{done}/{total}",
            "chips": [
                "Fulfill these requirements",
                "Show requirements",
                "What credentials are missing?",
                "Enterprise playbooks",
            ],
        },
    }


def fulfillment_event(req: dict[str, Any], *, message: str = "", solution: dict | None = None) -> dict[str, Any]:
    checklist = list(req.get("checklist") or [])
    done = sum(1 for c in checklist if c.get("done"))
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
            "chips": [
                "approve",
                "run test",
                "deploy",
                "Show requirements",
            ],
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
    parts = [
        req.get("goal") or req.get("raw") or "Automate this work",
        f"Field: {req.get('field')}.",
        f"Trigger: {req.get('trigger')}.",
        f"Data source: {req.get('data')}.",
        f"Output channel: {req.get('output')}.",
    ]
    if req.get("needs_approval"):
        parts.append("Ask me before acting (HITL).")
    if req.get("sla"):
        parts.append(f"SLA target: {req['sla']}.")
    return " ".join(parts)


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
    req = parse_requirements(body, last_field=aios.get("last_field"))
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
            req = parse_requirements(body, last_field=aios.get("last_field"))
        elif not req:
            return show_requirements_action(db, conversation_id)

    goal = compose_goal_from_requirements(req)
    result = compile_solution_blueprint(db, workspace_id, goal)
    recipe_name = result.get("recipe_name") or (result.get("recipe") or {}).get("name")
    field = (result.get("recipe") or {}).get("field") or req.get("field")

    mark_checklist(req, "goal", True)
    mark_checklist(req, "field", True)
    mark_checklist(req, "plan", True)
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
