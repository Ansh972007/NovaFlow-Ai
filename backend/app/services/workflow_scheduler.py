import logging
from datetime import datetime

from app.database import SessionLocal, Workflow, WorkflowSchedule
from app.services.cron_schedule import next_cron_run, validate_cron
from app.services.workflow import run_workflow

logger = logging.getLogger("novaflow.workflow_scheduler")


def schedule_dict(row: WorkflowSchedule) -> dict:
    return {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "cron_expression": row.cron_expression,
        "input_text": row.input_text or "",
        "enabled": bool(row.enabled),
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
    }


def compute_schedule_next_run(sched: WorkflowSchedule, base: datetime | None = None) -> datetime:
    return next_cron_run(sched.cron_expression, base)


async def tick_workflow_schedules() -> None:
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        due = (
            db.query(WorkflowSchedule)
            .filter(WorkflowSchedule.enabled == 1)
            .filter(WorkflowSchedule.next_run_at.isnot(None))
            .filter(WorkflowSchedule.next_run_at <= now)
            .all()
        )
        for sched in due:
            wf = db.get(Workflow, sched.workflow_id)
            if not wf or wf.status != 1:
                sched.enabled = 0
                db.commit()
                continue
            try:
                await run_workflow(
                    db,
                    wf,
                    sched.user_id,
                    (sched.input_text or "Scheduled run").strip(),
                    sched.workspace_id,
                )
                sched.last_run_at = now
                sched.next_run_at = compute_schedule_next_run(sched, now)
                sched.update_time = now
                db.commit()
            except Exception as exc:
                logger.warning("Scheduled workflow %s failed: %s", sched.id, exc)
    finally:
        db.close()
