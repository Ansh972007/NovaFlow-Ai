import asyncio
import logging
from datetime import datetime, timedelta

from app.database import EvalSchedule, EvalSuite, SessionLocal
from app.services.evaluation import compute_schedule_next_run, run_eval_suite

logger = logging.getLogger("novaflow.scheduler")

TERMINAL_FINETUNE = {"succeeded", "failed", "cancelled", "completed"}


async def eval_scheduler_loop(stop_event: asyncio.Event, interval_sec: int = 60) -> None:
    while not stop_event.is_set():
        try:
            await tick_eval_schedules()
        except Exception as exc:
            logger.warning("Eval scheduler tick failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
        except asyncio.TimeoutError:
            pass


async def tick_eval_schedules() -> None:
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        due = (
            db.query(EvalSchedule)
            .filter(EvalSchedule.enabled == 1)
            .filter(EvalSchedule.next_run_at.isnot(None))
            .filter(EvalSchedule.next_run_at <= now)
            .all()
        )
        for sched in due:
            suite = db.get(EvalSuite, sched.suite_id)
            if not suite:
                sched.enabled = 0
                db.commit()
                continue
            try:
                from app.platform.worker import worker_tenant

                with worker_tenant(
                    sched.workspace_id,
                    user_id=sched.user_id,
                    source="eval_scheduler",
                    job_type="eval_suite",
                    job_id=str(sched.id),
                    db=db,
                ):
                    await run_eval_suite(
                        db,
                        suite,
                        sched.user_id,
                        sched.workspace_id,
                        scoring=sched.scoring or "rules",
                        judge_threshold=sched.judge_threshold or 4,
                        webhook_url=sched.webhook_url or "",
                    )
                sched.last_run_at = now
                sched.next_run_at = compute_schedule_next_run(sched, now)
                sched.update_time = now
                db.commit()
            except Exception as exc:
                logger.warning("Scheduled eval %s failed: %s", sched.id, exc)
    finally:
        db.close()


async def tick_finetune_webhooks() -> None:
    from app.database import FineTuneJob
    from app.services.finetune import refresh_finetune_job, send_finetune_webhook_if_needed

    db = SessionLocal()
    try:
        pending = (
            db.query(FineTuneJob)
            .filter(FineTuneJob.job_id != "")
            .filter(FineTuneJob.webhook_sent == 0)
            .filter(FineTuneJob.webhook_url != "")
            .filter(FineTuneJob.status.notin_(list(TERMINAL_FINETUNE)))
            .limit(20)
            .all()
        )
        for job in pending:
            prev_status = job.status
            job = await refresh_finetune_job(db, job)
            if job.status != prev_status:
                await send_finetune_webhook_if_needed(db, job)
    finally:
        db.close()


async def background_scheduler_loop(stop_event: asyncio.Event) -> None:
    finetune_counter = 0
    maintenance_counter = 0
    while not stop_event.is_set():
        try:
            await tick_eval_schedules()
        except Exception as exc:
            logger.warning("Eval scheduler tick failed: %s", exc)
        try:
            from app.services.workflow_scheduler import tick_workflow_schedules

            await tick_workflow_schedules()
        except Exception as exc:
            logger.warning("Workflow scheduler tick failed: %s", exc)
        finetune_counter += 1
        maintenance_counter += 1
        if finetune_counter >= 5:
            finetune_counter = 0
            try:
                await tick_finetune_webhooks()
            except Exception as exc:
                logger.warning("Finetune webhook tick failed: %s", exc)
        if maintenance_counter >= 30:
            maintenance_counter = 0
            try:
                from app.platform_intelligence.automation.tasks import platform_maintenance_tick

                await platform_maintenance_tick()
            except Exception as exc:
                logger.warning("Platform maintenance tick failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
