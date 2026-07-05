from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import Assistant, KnowledgeBase, UsageEvent, Workflow, WorkflowRun, User, get_db
from app.deps import get_current_user, require_admin
from app.schemas import ok, fail

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.user_id
    since = datetime.utcnow() - timedelta(days=7)

    assistants_total = db.query(Assistant).filter(Assistant.user_id == uid).count()
    assistants_online = db.query(Assistant).filter(Assistant.user_id == uid, Assistant.status == 1).count()
    knowledge_total = db.query(KnowledgeBase).filter(KnowledgeBase.user_id == uid).count()
    workflows_total = db.query(Workflow).filter(Workflow.user_id == uid).count()
    workflows_published = db.query(Workflow).filter(Workflow.user_id == uid, Workflow.status == 1).count()
    workflow_runs = db.query(WorkflowRun).filter(WorkflowRun.user_id == uid).count()
    workflow_runs_7d = (
        db.query(WorkflowRun).filter(WorkflowRun.user_id == uid, WorkflowRun.create_time >= since).count()
    )
    chat_events_7d = (
        db.query(UsageEvent)
        .filter(UsageEvent.user_id == uid, UsageEvent.event_type == "chat", UsageEvent.create_time >= since)
        .count()
    )
    workflow_chat_7d = (
        db.query(UsageEvent)
        .filter(UsageEvent.user_id == uid, UsageEvent.event_type == "workflow_chat", UsageEvent.create_time >= since)
        .count()
    )

    recent_runs = (
        db.query(WorkflowRun, Workflow)
        .join(Workflow, WorkflowRun.workflow_id == Workflow.id)
        .filter(WorkflowRun.user_id == uid)
        .order_by(WorkflowRun.create_time.desc())
        .limit(5)
        .all()
    )

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
                for run, wf in recent_runs
            ],
        }
    )


@router.get("/analytics/timeseries")
def analytics_timeseries(days: int = 7, db: Session = Depends(get_db), user=Depends(get_current_user)):
    days = max(1, min(days, 30))
    uid = user.user_id
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        buckets[d] = {"date": d, "chat": 0, "workflow_run": 0, "workflow_chat": 0}

    events = (
        db.query(UsageEvent)
        .filter(UsageEvent.user_id == uid, UsageEvent.create_time >= start)
        .all()
    )
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

    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.user_id == uid, WorkflowRun.create_time >= start)
        .all()
    )
    for run in runs:
        if not run.create_time:
            continue
        key = run.create_time.date().isoformat()
        if key in buckets:
            buckets[key]["workflow_run"] += 1

    series = [buckets[k] for k in sorted(buckets.keys())]
    return ok({"days": days, "series": series})


@router.get("/analytics/assistants")
def analytics_assistants(days: int = 7, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.user_id
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 30)))

    rows = (
        db.query(UsageEvent)
        .filter(
            UsageEvent.user_id == uid,
            UsageEvent.event_type.in_(["chat", "workflow_chat"]),
            UsageEvent.create_time >= since,
        )
        .all()
    )

    counts: dict[str, int] = defaultdict(int)
    for ev in rows:
        counts[ev.resource_id or "unknown"] += 1

    assistants = {
        a.id: a.name
        for a in db.query(Assistant).filter(Assistant.user_id == uid).all()
    }
    workflows = {
        w.id: w.name
        for w in db.query(Workflow).filter(Workflow.user_id == uid).all()
    }

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
    user=Depends(get_current_user),
):
    uid = user.user_id
    assistant = db.get(Assistant, assistant_id)
    if not assistant or assistant.user_id != uid:
        return fail(404, "Assistant not found")

    days = max(1, min(days, 30))
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        buckets[d] = {"date": d, "messages": 0}

    events = (
        db.query(UsageEvent)
        .filter(
            UsageEvent.user_id == uid,
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
def team_members(db: Session = Depends(get_db), user=Depends(require_admin)):
    members = db.query(User).filter(User.delete == 0).order_by(User.user_id).all()
    return ok(
        [
            {
                "user_id": m.user_id,
                "user_name": m.user_name,
                "role": m.role or "editor",
                "create_time": m.create_time.isoformat() if m.create_time else None,
            }
            for m in members
        ]
    )


@router.patch("/team/members/{member_id}/role")
def update_member_role(
    member_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    role = (body.get("role") or "").strip().lower()
    if role not in {"admin", "editor", "viewer"}:
        return fail(400, "Invalid role")
    member = db.get(User, member_id)
    if not member or member.delete:
        return fail(404, "User not found")
    if member.user_id == user.user_id and role != "admin":
        return fail(400, "Cannot demote yourself")
    member.role = role
    db.commit()
    return ok({"user_id": member.user_id, "role": member.role})
