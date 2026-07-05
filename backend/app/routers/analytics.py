from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import Assistant, KnowledgeBase, UsageEvent, Workflow, WorkflowRun, get_db
from app.deps import get_current_user
from app.schemas import ok

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
            "chat_messages_7d": chat_events_7d,
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
