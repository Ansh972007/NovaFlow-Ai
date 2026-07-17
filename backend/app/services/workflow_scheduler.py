import logging
from datetime import datetime

from app.database import SessionLocal, Workflow, WorkflowSchedule
from app.platform.worker import worker_tenant
from app.services.cron_schedule import next_cron_run
from app.services.workflow import run_workflow

logger = logging.getLogger("novaflow.workflow_scheduler")


def schedule_dict(row: WorkflowSchedule, workflow_name: str | None = None) -> dict:
    data = {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "cron_expression": row.cron_expression,
        "input_text": row.input_text or "",
        "enabled": bool(row.enabled),
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "workspace_id": row.workspace_id,
    }
    if workflow_name is not None:
        data["workflow_name"] = workflow_name
    return data


def compute_schedule_next_run(sched: WorkflowSchedule, base: datetime | None = None) -> datetime:
    return next_cron_run(sched.cron_expression, base)


async def run_schedule_now(db, schedule_id: int, workspace_id: int) -> dict:
    sched = db.get(WorkflowSchedule, schedule_id)
    if not sched or sched.workspace_id != workspace_id:
        raise ValueError("Schedule not found")
    wf = db.get(Workflow, sched.workflow_id)
    if not wf or wf.workspace_id != workspace_id:
        raise ValueError("Workflow not found")
    if wf.status != 1:
        raise ValueError("Workflow must be published")
    now = datetime.utcnow()
    with worker_tenant(
        workspace_id,
        user_id=sched.user_id,
        source="workflow_scheduler",
        job_type="workflow_schedule_manual",
        job_id=str(sched.id),
        db=db,
    ):
        result = await run_workflow(
            db,
            wf,
            sched.user_id,
            (sched.input_text or "Manual schedule run").strip(),
            sched.workspace_id,
        )
    sched.last_run_at = now
    sched.next_run_at = compute_schedule_next_run(sched, now)
    sched.update_time = now
    db.commit()
    db.refresh(sched)
    return {
        "schedule": schedule_dict(sched, wf.name),
        "run": result if isinstance(result, dict) else {"ok": True},
    }


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
            if not sched.workspace_id:
                sched.enabled = 0
                db.commit()
                continue
            wf = db.get(Workflow, sched.workflow_id)
            if not wf or wf.status != 1 or wf.workspace_id != sched.workspace_id:
                sched.enabled = 0
                db.commit()
                continue
            try:
                with worker_tenant(
                    sched.workspace_id,
                    user_id=sched.user_id,
                    source="workflow_scheduler",
                    job_type="workflow_schedule",
                    job_id=str(sched.id),
                    db=db,
                ):
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
