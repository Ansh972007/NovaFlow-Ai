from datetime import datetime, timedelta
from collections import defaultdict
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import (
    Assistant,
    KnowledgeBase,
    SecurityAuditLog,
    UsageEvent,
    Workflow,
    WorkflowRun,
    User,
    WorkspaceMember,
    get_db,
)
from app.deps import require_permission
from app.schemas import ok, fail
from app.security.rbac import Permission

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    since = datetime.utcnow() - timedelta(days=7)

    assistants_total = ctx.query(Assistant).count()
    assistants_online = ctx.query(Assistant).filter(Assistant.status == 1).count()
    knowledge_total = ctx.query(KnowledgeBase).count()
    workflows_total = ctx.query(Workflow).count()
    workflows_published = ctx.query(Workflow).filter(Workflow.status == 1).count()
    workflow_runs = ctx.query(WorkflowRun).count()
    workflow_runs_7d = ctx.query(WorkflowRun).filter(WorkflowRun.create_time >= since).count()
    chat_events_7d = (
        ctx.query(UsageEvent)
        .filter(UsageEvent.event_type == "chat", UsageEvent.create_time >= since)
        .count()
    )
    workflow_chat_7d = (
        ctx.query(UsageEvent)
        .filter(UsageEvent.event_type == "workflow_chat", UsageEvent.create_time >= since)
        .count()
    )

    recent_runs = (
        ctx.query(WorkflowRun)
        .join(Workflow, WorkflowRun.workflow_id == Workflow.id)
        .order_by(WorkflowRun.create_time.desc())
        .limit(5)
        .all()
    )
    # Re-attach workflow names
    recent_payload = []
    for run in recent_runs:
        wf = ctx.fetch(Workflow, run.workflow_id)
        if not wf:
            continue
        recent_payload.append((run, wf))

    return ok(
        {
            "assistants_total": assistants_total,
            "assistants_online": assistants_online,
            "knowledge_total": knowledge_total,
            "workflows_total": workflows_total,
            "workflows_published": workflows_published,
            "workflow_runs_total": workflow_runs,
            "workflow_runs_7d": workflow_runs_7d,
            "chat_messages_7d": chat_events_7d + workflow_chat_7d,
            "recent_runs": [
                {
                    "id": run.id,
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "duration_ms": run.duration_ms,
                    "create_time": run.create_time.isoformat() if run.create_time else None,
                }
                for run, wf in recent_payload
            ],
        }
    )


@router.get("/analytics/timeseries")
def analytics_timeseries(
    days: int = 7,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    days = max(1, min(days, 30))
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        buckets[d] = {"date": d, "chat": 0, "workflow_run": 0, "workflow_chat": 0}

    events = ctx.query(UsageEvent).filter(UsageEvent.create_time >= start).all()
    for ev in events:
        if not ev.create_time:
            continue
        key = ev.create_time.date().isoformat()
        if key not in buckets:
            continue
        if ev.event_type == "chat":
            buckets[key]["chat"] += 1
        elif ev.event_type == "workflow_chat":
            buckets[key]["workflow_chat"] += 1

    runs = ctx.query(WorkflowRun).filter(WorkflowRun.create_time >= start).all()
    for run in runs:
        if not run.create_time:
            continue
        key = run.create_time.date().isoformat()
        if key in buckets:
            buckets[key]["workflow_run"] += 1

    series = [buckets[k] for k in sorted(buckets.keys())]
    return ok({"days": days, "series": series})


@router.get("/analytics/assistants")
def analytics_assistants(
    days: int = 7,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 30)))

    rows = (
        ctx.query(UsageEvent)
        .filter(
            UsageEvent.event_type.in_(["chat", "workflow_chat"]),
            UsageEvent.create_time >= since,
        )
        .all()
    )

    counts: dict[str, int] = defaultdict(int)
    for ev in rows:
        counts[ev.resource_id or "unknown"] += 1

    assistants = {a.id: a.name for a in ctx.query(Assistant).all()}
    workflows = {w.id: w.name for w in ctx.query(Workflow).all()}

    items = []
    for rid, count in sorted(counts.items(), key=lambda x: -x[1])[:12]:
        label = assistants.get(rid) or workflows.get(rid) or rid[:8]
        kind = "workflow" if rid in workflows else "assistant"
        items.append({"id": rid, "name": label, "count": count, "kind": kind})

    return ok({"items": items, "days": days})


@router.get("/analytics/assistants/{assistant_id}")
def analytics_assistant_detail(
    assistant_id: str,
    days: int = 7,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    assistant = ctx.fetch(Assistant, assistant_id)
    if not assistant:
        return fail(404, "Assistant not found")

    days = max(1, min(days, 30))
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        buckets[d] = {"date": d, "messages": 0}

    events = (
        ctx.query(UsageEvent)
        .filter(
            UsageEvent.event_type == "chat",
            UsageEvent.resource_id == assistant_id,
            UsageEvent.create_time >= start,
        )
        .all()
    )
    for ev in events:
        if not ev.create_time:
            continue
        key = ev.create_time.date().isoformat()
        if key in buckets:
            buckets[key]["messages"] += 1

    series = [buckets[k] for k in sorted(buckets.keys())]
    return ok(
        {
            "assistant_id": assistant_id,
            "name": assistant.name,
            "status": assistant.status,
            "total_messages": len(events),
            "days": days,
            "series": series,
        }
    )


@router.get("/team/members")
def team_members(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.TEAM_MANAGE))):
    """Workspace members (tenant-scoped). Prefer /workspaces/{id}/members for new clients."""
    rows = (
        db.query(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.user_id)
        .filter(WorkspaceMember.workspace_id == ctx.workspace_id, User.delete == 0)
        .order_by(User.user_id)
        .all()
    )
    return ok(
        [
            {
                "user_id": u.user_id,
                "user_name": u.user_name,
                "role": m.role or "editor",
                "create_time": m.create_time.isoformat() if m.create_time else None,
            }
            for m, u in rows
        ]
    )


@router.patch("/team/members/{member_id}/role")
def update_member_role(
    member_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.TEAM_MANAGE)),
):
    from app.platform.roles import WORKSPACE_ROLES, normalize_workspace_role

    role = normalize_workspace_role(body.get("role") or "")
    if role not in WORKSPACE_ROLES or role == "owner":
        return fail(400, "Invalid role")
    row = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == ctx.workspace_id,
            WorkspaceMember.user_id == member_id,
        )
        .first()
    )
    if not row:
        return fail(404, "Member not found")
    if member_id == ctx.user.user_id and role != "admin":
        return fail(400, "Cannot demote yourself")
    row.role = role
    db.commit()
    ctx.audit(
        "workspace.member.role_changed",
        resource_type="workspace_member",
        resource_id=str(member_id),
        detail={"role": role},
    )
    return ok({"user_id": member_id, "role": role})


@router.get("/analytics/audit")
def list_audit_events(
    days: int = 7,
    limit: int = 100,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.SECURITY_AUDIT)),
):
    """Tenant-scoped security audit trail (immutable SecurityAuditLog)."""
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 500))
    since = datetime.utcnow() - timedelta(days=days)
    events = (
        ctx.query(SecurityAuditLog)
        .filter(SecurityAuditLog.created_at >= since)
        .order_by(SecurityAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return ok(
        [
            {
                "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                "user_id": ev.actor_user_id,
                "event_type": ev.action,
                "resource_id": ev.resource_id or "",
                "resource_type": ev.resource_type or "",
                "success": bool(ev.success),
                "meta": ev.detail_json or "",
            }
            for ev in events
        ]
    )


@router.get("/analytics/export")
def export_audit_log(
    days: int = 30,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_EXPORT)),
):
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)

    events = (
        ctx.query(SecurityAuditLog)
        .filter(SecurityAuditLog.created_at >= since)
        .order_by(SecurityAuditLog.created_at.desc())
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "user_id", "action", "resource_type", "resource_id", "success", "detail"])
    for ev in events:
        writer.writerow(
            [
                ev.created_at.isoformat() if ev.created_at else "",
                ev.actor_user_id or "",
                ev.action,
                ev.resource_type or "",
                ev.resource_id or "",
                ev.success,
                ev.detail_json or "",
            ]
        )

    buf.seek(0)
    filename = f"novaflow-audit-{datetime.utcnow().date().isoformat()}.csv"
    ctx.audit("audit.exported", resource_type="security_audit", detail={"days": days, "rows": len(events)})
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/analytics/ab-routing")
def analytics_ab_routing(
    days: int = 30,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    import json

    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))
    rows = (
        ctx.query(UsageEvent)
        .filter(
            UsageEvent.event_type == "chat",
            UsageEvent.create_time >= since,
        )
        .all()
    )
    base = 0
    variant = 0
    unknown = 0
    for ev in rows:
        try:
            meta = json.loads(ev.meta or "{}")
        except json.JSONDecodeError:
            meta = {}
        v = meta.get("ab_variant")
        if v == "variant":
            variant += 1
        elif v == "base":
            base += 1
        else:
            unknown += 1
    total = base + variant
    return ok(
        {
            "days": days,
            "base_count": base,
            "variant_count": variant,
            "untracked_count": unknown,
            "variant_pct": round((variant / total) * 100, 1) if total else 0,
        }
    )
