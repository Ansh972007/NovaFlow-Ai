"""Enterprise Peak Chat ops — schedules, EIAP, audit, export/share, vault, integrations, RBAC."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import Conversation, SecurityAuditLog, Workflow, WorkflowSchedule
from app.platform.roles import has_workspace_min_role
from app.services.cron_schedule import next_cron_run, validate_cron
from app.services.workflow_scheduler import schedule_dict

logger = logging.getLogger(__name__)


def _helpers():
    from app.composer import chat_actions as ca

    return ca


DANGEROUS_INTENTS = frozenset(
    {
        "run_workflow",
        "schedule_create",
        "schedule_pause",
        "share_conversation",
        "export_conversation",
        "index_attachment",
        "approve_recommendation",
        "test_notification",
        "stop_run",
        "fulfill_requirements",
        "capture_requirements",
        "incident_kill_switch",
        "restore_version",
        "apply_change_request",
        "collab_war_room",
    }
)

EDITOR_MIN = "editor"


def denied_event(*, message: str, required_role: str = EDITOR_MIN) -> dict[str, Any]:
    return {
        "events": [
            {
                "type": "aios_denied",
                "data": {
                    "message": message,
                    "required_role": required_role,
                    "chips": ["What can you do?", "Workspace health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": message,
    }


def gate_role(workspace_role: str | None, intent: str) -> dict[str, Any] | None:
    if intent not in DANGEROUS_INTENTS:
        return None
    if has_workspace_min_role(workspace_role, EDITOR_MIN):
        return None
    return denied_event(
        message=f"Your role (`{workspace_role or 'viewer'}`) cannot run `{intent}`. Need **{EDITOR_MIN}+**.",
        required_role=EDITOR_MIN,
    )


def parse_natural_cron(text: str) -> str | None:
    """Map common phrases to cron; also accept raw 5-field cron."""
    t = (text or "").lower().strip()
    raw = re.search(r"\b(\d{1,2}\s+\d{1,2}\s+\S+\s+\S+\s+\S+)\b", t)
    if raw:
        try:
            return validate_cron(raw.group(1))
        except ValueError:
            pass

    hour = 9
    hm = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t)
    if hm:
        hour = int(hm.group(1))
        ampm = (hm.group(3) or "").lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        minute = int(hm.group(2) or 0)
    else:
        minute = 0

    if re.search(r"\bevery\s+hour\b|\bhourly\b", t):
        return f"{minute} * * * *"
    if re.search(r"\bdaily\b|\bevery\s+day\b", t):
        return f"{minute} {hour} * * *"
    dow_map = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 0,
    }
    for name, dow in dow_map.items():
        if name in t or re.search(rf"\bevery\s+{name}\b", t):
            return f"{minute} {hour} * * {dow}"
    if re.search(r"\bweekly\b", t):
        return f"{minute} {hour} * * 1"
    if re.search(r"\bschedule\b", t) and not re.search(r"\blist\b|\bpause\b|\bshow\b", t):
        return f"{minute} {hour} * * *"
    return None


def list_schedules_action(db: Session, workspace_id: int) -> dict[str, Any]:
    rows = (
        db.query(WorkflowSchedule)
        .filter(WorkflowSchedule.workspace_id == workspace_id)
        .order_by(WorkflowSchedule.create_time.desc())
        .limit(20)
        .all()
    )
    items = []
    for r in rows:
        wf = db.get(Workflow, r.workflow_id)
        items.append(schedule_dict(r, workflow_name=wf.name if wf else None))
    return {
        "events": [
            {
                "type": "aios_schedule",
                "data": {
                    "status": "list",
                    "schedules": items,
                    "count": len(items),
                    "chips": ["Schedule my last workflow daily at 9am", "Workspace health"],
                    "links": {"schedules": "/workflows?tab=schedules"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Found {len(items)} schedule(s).",
    }


def create_schedule_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    wf = ca._find_workflow(db, workspace_id, text, aios)
    if not wf:
        return {
            "events": [
                {
                    "type": "aios_schedule",
                    "data": {"status": "error", "message": "No workflow found to schedule. Deploy one first."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No workflow to schedule.",
        }
    if int(wf.status or 0) != 1:
        return {
            "events": [
                {
                    "type": "aios_schedule",
                    "data": {"status": "error", "message": "Publish/deploy the workflow before scheduling."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Workflow must be published.",
        }
    cron = parse_natural_cron(text)
    if not cron:
        return {
            "events": [
                {
                    "type": "aios_schedule",
                    "data": {
                        "status": "error",
                        "message": "Could not parse schedule. Try: daily at 9am, every Monday 9am, every hour.",
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Unrecognized schedule phrase.",
        }
    try:
        cron = validate_cron(cron)
    except ValueError as exc:
        return {
            "events": [{"type": "aios_schedule", "data": {"status": "error", "message": str(exc)}}],
            "blocked_normal_reply": True,
            "summary": str(exc),
        }
    now = datetime.utcnow()
    row = WorkflowSchedule(
        workflow_id=wf.id,
        workspace_id=workspace_id,
        user_id=user_id,
        cron_expression=cron,
        input_text=(aios.get("goal") or "Scheduled from chat")[:2000],
        enabled=1,
    )
    db.add(row)
    db.flush()
    row.next_run_at = next_cron_run(cron, now)
    db.commit()
    db.refresh(row)
    ca.audit_chat_action(
        db,
        action="schedule_create",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="schedule",
        resource_id=str(row.id),
        detail={"cron": cron, "workflow_id": wf.id},
    )
    data = schedule_dict(row, workflow_name=wf.name)
    data["status"] = "created"
    data["message"] = f"Scheduled **{wf.name}** with `{cron}`."
    data["chips"] = ["List schedules", "Pause schedule " + str(row.id)]
    data["links"] = {"workflow": f"/workflows/{wf.id}", "schedules": "/workflows?tab=schedules"}
    return {
        "events": [{"type": "aios_schedule", "data": data}],
        "blocked_normal_reply": True,
        "summary": data["message"],
    }


def pause_schedule_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
) -> dict[str, Any]:
    m = re.search(r"schedule\s+#?(\d+)", text or "", re.I)
    sid = int(m.group(1)) if m else None
    row = None
    if sid:
        row = db.get(WorkflowSchedule, sid)
        if row and int(row.workspace_id or 0) != int(workspace_id):
            row = None
    if not row:
        row = (
            db.query(WorkflowSchedule)
            .filter(WorkflowSchedule.workspace_id == workspace_id, WorkflowSchedule.enabled == 1)
            .order_by(WorkflowSchedule.create_time.desc())
            .first()
        )
    if not row:
        return {
            "events": [{"type": "aios_schedule", "data": {"status": "error", "message": "No schedule to pause."}}],
            "blocked_normal_reply": True,
            "summary": "No schedule found.",
        }
    row.enabled = 0
    db.commit()
    ca = _helpers()
    ca.audit_chat_action(
        db,
        action="schedule_pause",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="schedule",
        resource_id=str(row.id),
    )
    data = schedule_dict(row)
    data["status"] = "paused"
    data["message"] = f"Paused schedule `{row.id}`."
    return {
        "events": [{"type": "aios_schedule", "data": data}],
        "blocked_normal_reply": True,
        "summary": data["message"],
    }


def compliance_action(db: Session, workspace_id: int, text: str) -> dict[str, Any]:
    from app.eiap.governance import compliance_report, security_posture

    if re.search(r"\bsecurity posture\b", text or "", re.I):
        posture = security_posture(db, workspace_id=workspace_id)
        return {
            "events": [
                {
                    "type": "aios_compliance",
                    "data": {
                        "kind": "security_posture",
                        "title": "Security posture",
                        **posture,
                        "chips": ["Compliance report", "Workspace health"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Security posture report ready.",
        }
    report = compliance_report(db, workspace_id=workspace_id)
    return {
        "events": [
            {
                "type": "aios_compliance",
                "data": {
                    "kind": "compliance",
                    "title": "Compliance brief",
                    **report,
                    "chips": ["Security posture", "Show my recent chat actions"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Compliance status: {report.get('compliance_status')}.",
    }


def finops_action(db: Session, workspace_id: int) -> dict[str, Any]:
    from app.eiap.finops import cost_analysis

    analysis = cost_analysis(db, workspace_id=workspace_id, days=30)
    summary = analysis.get("summary") or {}
    return {
        "events": [
            {
                "type": "aios_finops",
                "data": {
                    "title": "FinOps summary (30d)",
                    "summary": summary,
                    "forecast": analysis.get("forecast"),
                    "anomalies": (analysis.get("anomalies") or [])[:8],
                    "model_costs": (analysis.get("model_costs") or [])[:8],
                    "chips": ["Workspace health", "Show recommendations"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "FinOps cost summary ready.",
    }


def health_action(db: Session, workspace_id: int) -> dict[str, Any]:
    from app.eiap.governance import workspace_health_report

    report = workspace_health_report(db, workspace_id=workspace_id)
    return {
        "events": [
            {
                "type": "aios_health",
                "data": {
                    "title": "Workspace health",
                    **report,
                    "chips": ["Show recommendations", "FinOps summary", "Compliance report"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Workspace posture: {report.get('posture')}.",
    }


def recommendations_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
    intent: str,
) -> dict[str, Any]:
    from app.eiap.recommendations import get_recommendation, list_recommendations, recommendation_dict, set_status

    if intent == "approve_recommendation":
        m = re.search(r"recommendation\s+([a-f0-9]{8,})", text or "", re.I)
        rid = m.group(1) if m else ""
        rec = get_recommendation(db, rid, workspace_id=workspace_id) if rid else None
        if not rec:
            open_recs = list_recommendations(db, workspace_id=workspace_id, status="open", limit=1)
            rec = open_recs[0] if open_recs else None
        if not rec:
            return {
                "events": [
                    {
                        "type": "aios_recommendation",
                        "data": {"status": "error", "message": "No open recommendation to approve."},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "No recommendation found.",
            }
        set_status(db, rec, status="approved", reviewed_by=user_id)
        ca = _helpers()
        ca.audit_chat_action(
            db,
            action="approve_recommendation",
            user_id=user_id,
            workspace_id=workspace_id,
            resource_type="recommendation",
            resource_id=rec.id,
        )
        return {
            "events": [
                {
                    "type": "aios_recommendation",
                    "data": {
                        "status": "approved",
                        "recommendation": recommendation_dict(rec),
                        "message": f"Approved recommendation: {rec.title}",
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": f"Approved: {rec.title}",
        }

    rows = list_recommendations(db, workspace_id=workspace_id, status="open", limit=12)
    items = [recommendation_dict(r) for r in rows]
    chips = [f"Approve recommendation {i['id'][:12]}" for i in items[:3]]
    chips.append("Workspace health")
    return {
        "events": [
            {
                "type": "aios_recommendation",
                "data": {
                    "status": "list",
                    "recommendations": items,
                    "count": len(items),
                    "chips": chips,
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"{len(items)} open recommendation(s).",
    }


def export_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.conversation.export import export_conversation

    if not conversation_id:
        return {
            "events": [{"type": "aios_export", "data": {"status": "error", "message": "No active conversation."}}],
            "blocked_normal_reply": True,
            "summary": "Open a chat first.",
        }
    fmt = "markdown"
    if re.search(r"\bjson\b", text or "", re.I):
        fmt = "json"
    elif re.search(r"\bhtml\b", text or "", re.I):
        fmt = "html"
    result = export_conversation(db, conversation_id, workspace_id=workspace_id, fmt=fmt)
    if result.get("error"):
        return {
            "events": [{"type": "aios_export", "data": {"status": "error", "message": result["error"]}}],
            "blocked_normal_reply": True,
            "summary": result["error"],
        }
    content = result.get("content") or ""
    ca = _helpers()
    ca.audit_chat_action(
        db,
        action="export_conversation",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="conversation",
        resource_id=conversation_id,
        detail={"format": fmt, "chars": len(content)},
    )
    return {
        "events": [
            {
                "type": "aios_export",
                "data": {
                    "status": "ok",
                    "format": fmt,
                    "content": content[:12000],
                    "truncated": len(content) > 12000,
                    "message": f"Exported conversation as {fmt}.",
                    "chips": ["Share this chat read-only for 72h"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Exported as {fmt} ({len(content)} chars).",
    }


def share_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.conversation.collaboration import create_share_link

    if not conversation_id:
        return {
            "events": [{"type": "aios_share", "data": {"status": "error", "message": "No active conversation."}}],
            "blocked_normal_reply": True,
            "summary": "Open a chat first.",
        }
    conv = db.get(Conversation, conversation_id)
    if not conv or int(conv.workspace_id or 0) != int(workspace_id):
        return {
            "events": [{"type": "aios_share", "data": {"status": "error", "message": "Conversation not found."}}],
            "blocked_normal_reply": True,
            "summary": "Conversation not found.",
        }
    hours = 72
    hm = re.search(r"(\d+)\s*h", text or "", re.I)
    if hm:
        hours = max(1, min(168, int(hm.group(1))))
    perm = "read"
    if re.search(r"\bwrite\b|\bedit\b", text or "", re.I):
        perm = "write"
    link = create_share_link(db, conv, created_by=user_id, permission=perm, expires_hours=hours)
    ca = _helpers()
    ca.audit_chat_action(
        db,
        action="share_conversation",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="conversation",
        resource_id=conversation_id,
        detail={"permission": perm, "hours": hours},
    )
    path = f"/chat?share={link['share_token']}"
    return {
        "events": [
            {
                "type": "aios_share",
                "data": {
                    "status": "ok",
                    "permission": link["permission"],
                    "expires_at": link["expires_at"],
                    "share_token": link["share_token"],
                    "path": path,
                    "message": f"Share link created ({perm}, {hours}h).",
                    "chips": ["Export this chat as markdown"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Share link ready: {path}",
    }


async def meta_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
    intent: str,
) -> dict[str, Any]:
    from app.conversation.ai_features import generate_title, suggest_tags
    from app.conversation.memory import summarize_conversation
    from app.runtime.context import runtime_from_platform

    if not conversation_id:
        return {
            "events": [{"type": "aios_meta", "data": {"status": "error", "message": "No active conversation."}}],
            "blocked_normal_reply": True,
            "summary": "Open a chat first.",
        }
    conv = db.get(Conversation, conversation_id)
    if not conv or int(conv.workspace_id or 0) != int(workspace_id):
        return {
            "events": [{"type": "aios_meta", "data": {"status": "error", "message": "Conversation not found."}}],
            "blocked_normal_reply": True,
            "summary": "Conversation not found.",
        }
    ctx = _helpers().build_platform_ctx(db, user_id=user_id, workspace_id=workspace_id)
    rt = runtime_from_platform(ctx)
    try:
        if intent == "title_conversation":
            title = await generate_title(rt, conv)
            _helpers().audit_chat_action(
                db, action="title_conversation", user_id=user_id, workspace_id=workspace_id, resource_id=conversation_id
            )
            return {
                "events": [
                    {
                        "type": "aios_meta",
                        "data": {"status": "titled", "title": title, "message": f"Title set to: {title}"},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": f"Title: {title}",
            }
        if intent == "tag_conversation":
            tags = await suggest_tags(rt, conv)
            _helpers().audit_chat_action(
                db, action="tag_conversation", user_id=user_id, workspace_id=workspace_id, resource_id=conversation_id
            )
            return {
                "events": [
                    {
                        "type": "aios_meta",
                        "data": {
                            "status": "tagged",
                            "tags": tags,
                            "message": f"Tags: {', '.join(tags) if tags else 'none'}",
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": f"Tags: {', '.join(tags) if tags else 'none'}",
            }
        summary = await summarize_conversation(rt, conv)
        _helpers().audit_chat_action(
            db, action="summarize_conversation", user_id=user_id, workspace_id=workspace_id, resource_id=conversation_id
        )
        return {
            "events": [
                {
                    "type": "aios_meta",
                    "data": {
                        "status": "summarized",
                        "summary": summary,
                        "message": "Conversation summarized.",
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": summary or "Summary empty.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("meta_action failed")
        return {
            "events": [{"type": "aios_meta", "data": {"status": "error", "message": str(exc)[:400]}}],
            "blocked_normal_reply": True,
            "summary": f"Meta action failed: {exc}",
        }


def audit_trail_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
) -> dict[str, Any]:
    q = db.query(SecurityAuditLog).filter(SecurityAuditLog.workspace_id == workspace_id)
    if re.search(r"\bmy\b|\bmy recent\b", text or "", re.I):
        q = q.filter(SecurityAuditLog.actor_user_id == user_id)
    if re.search(r"\bchat\b", text or "", re.I):
        q = q.filter(SecurityAuditLog.action.like("chat.%"))
    rows = q.order_by(SecurityAuditLog.created_at.desc()).limit(20).all()
    items = []
    for r in rows:
        items.append(
            {
                "action": r.action,
                "success": bool(r.success),
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "actor_user_id": r.actor_user_id,
            }
        )
    return {
        "events": [
            {
                "type": "aios_audit",
                "data": {
                    "title": "Audit trail",
                    "entries": items,
                    "count": len(items),
                    "chips": ["Compliance report", "Workspace health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"{len(items)} audit event(s).",
    }


def vault_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.services import credential_vault as vault

    if re.search(r"missing|what credentials", text or "", re.I):
        _, aios = _helpers()._load_aios(db, conversation_id)
        missing = aios.get("missing_credentials") or []
        return {
            "events": [
                {
                    "type": "aios_vault",
                    "data": {
                        "status": "gaps",
                        "missing": missing or [],
                        "message": "Missing for current plan"
                        if missing
                        else "No gaps recorded on this plan — vault entries below.",
                        "credentials_url": "/credentials",
                        "chips": ["List vault categories", "Open credentials"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": f"Missing: {', '.join(missing) if missing else 'none recorded'}.",
        }

    rows = vault.list_entries(db, workspace_id)
    cats: dict[str, int] = {}
    items = []
    for r in rows[:40]:
        cats[r.category or "other"] = cats.get(r.category or "other", 0) + 1
        items.append(
            {
                "id": r.id,
                "category": r.category,
                "kind": r.kind,
                "label": r.label,
                "is_default": bool(r.is_default),
            }
        )
    return {
        "events": [
            {
                "type": "aios_vault",
                "data": {
                    "status": "list",
                    "categories": cats,
                    "entries": items,
                    "count": len(items),
                    "message": "Vault posture (labels only — no secrets).",
                    "credentials_url": "/credentials",
                    "chips": ["What credentials are missing?", "Check Slack/Telegram status"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"{len(items)} vault entr(y/ies) across {len(cats)} categor(y/ies).",
    }


async def integration_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
    intent: str,
) -> dict[str, Any]:
    from app.services.workspace_integrations import integrations_dict

    settings = integrations_dict(db, workspace_id)
    channels = []
    for key in ("telegram", "slack", "discord", "smtp", "github"):
        block = settings.get(key) if isinstance(settings.get(key), dict) else {}
        configured = bool(block.get("configured") or block.get("token_configured") or block.get("bot_configured"))
        if key == "telegram":
            configured = bool(block.get("configured") or block.get("bot_token_masked"))
        if key == "smtp":
            configured = bool(block.get("configured") or block.get("host"))
        channels.append({"name": key, "configured": configured, "detail": {k: v for k, v in block.items() if "token" not in k.lower() or "masked" in k.lower()}})

    if intent == "test_notification":
        from app.services.integrations import send_notification

        channel = "slack"
        if re.search(r"telegram", text or "", re.I):
            channel = "telegram"
        elif re.search(r"discord", text or "", re.I):
            channel = "discord"
        elif re.search(r"email|smtp", text or "", re.I):
            channel = "email"
        try:
            result = await send_notification(
                channel,
                "",
                "NovaFlow chat test",
                f"NovaFlow chat test notification ({channel})",
                db=db,
                workspace_id=workspace_id,
            )
            ok = bool(result.get("ok") or result.get("success") or result.get("status") == "ok")
            _helpers().audit_chat_action(
                db,
                action="test_notification",
                user_id=user_id,
                workspace_id=workspace_id,
                detail={"channel": channel, "ok": ok},
                success=ok,
            )
            return {
                "events": [
                    {
                        "type": "aios_integration",
                        "data": {
                            "status": "tested",
                            "channel": channel,
                            "result": {k: result.get(k) for k in list(result.keys())[:12]},
                            "channels": channels,
                            "message": f"Test {channel} notification {'sent' if ok else 'failed'}.",
                            "chips": ["Check Slack/Telegram status", "List vault categories"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": f"Test notification ({channel}): {'ok' if ok else 'failed'}.",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "events": [
                    {
                        "type": "aios_integration",
                        "data": {
                            "status": "error",
                            "message": str(exc)[:400],
                            "channels": channels,
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": f"Notify failed: {exc}",
            }

    return {
        "events": [
            {
                "type": "aios_integration",
                "data": {
                    "status": "health",
                    "title": "Integrations health",
                    "channels": channels,
                    "chips": ["Send a test notification", "List vault categories"],
                    "links": {"settings": "/settings?tab=integrations"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Integrations health ready.",
    }


def playbook_action(text: str) -> dict[str, Any]:
    from app.composer.chat_playbooks import list_playbooks_event, match_playbook, playbook_event

    t = (text or "").lower()
    if re.search(r"\blist (enterprise )?playbooks\b|\benterprise playbooks\b|\bplaybooks\b", t) and not re.search(
        r"\brun\b|\bstart\b|\bincident\b|\bweekly\b|\bonboard\b", t
    ):
        ev = list_playbooks_event()
        return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["title"]}
    pb = match_playbook(text)
    if not pb:
        ev = list_playbooks_event()
        return {"events": [ev], "blocked_normal_reply": True, "summary": "Pick a playbook."}
    ev = playbook_event(pb)
    return {"events": [ev], "blocked_normal_reply": True, "summary": pb["title"]}
