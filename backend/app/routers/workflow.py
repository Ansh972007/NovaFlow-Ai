import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowRun, WorkflowSchedule, WorkflowVersion, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import WorkflowCreate, WorkflowRunRequest, WorkflowUpdate, fail, ok
from app.services.cron_schedule import validate_cron
from app.services.workflow import (
    TEMPLATES,
    list_workflow_versions,
    restore_workflow_version,
    resume_workflow_pending,
    run_workflow,
    snapshot_workflow_version,
    workflow_dict,
)
from app.services.workflow_scheduler import compute_schedule_next_run, schedule_dict

router = APIRouter(tags=["Workflow"])


@router.get("/workflow")
def list_workflows(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = db.query(Workflow).filter(Workflow.workspace_id == ctx.workspace_id)
    if status is not None:
        q = q.filter(Workflow.status == status)
    total = q.count()
    rows = q.order_by(Workflow.update_time.desc()).offset((page - 1) * limit).limit(limit).all()
    return ok({"data": [workflow_dict(w) for w in rows], "total": total})


@router.get("/workflow/templates")
def workflow_templates(ctx=Depends(get_workspace_ctx)):
    data = [
        {"id": tid, "name": tpl["name"], "desc": tpl["desc"], "graph": tpl["graph"]}
        for tid, tpl in TEMPLATES.items()
    ]
    return ok(data)


@router.get("/workflow/info/{workflow_id}")
def workflow_info(workflow_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    data = workflow_dict(w)
    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.create_time.desc())
        .limit(10)
        .all()
    )
    data["recent_runs"] = [
        {
            "id": r.id,
            "input": (r.input_text or "")[:120],
            "output": (r.output_text or "")[:120],
            "duration_ms": r.duration_ms,
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in runs
    ]
    data["run_count"] = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).count()
    return ok(data)


@router.post("/workflow")
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    tpl = TEMPLATES.get(body.template_id) or TEMPLATES["rag"]
    w = Workflow(
        name=body.name.strip() or tpl["name"],
        desc=body.desc or tpl.get("desc", ""),
        graph_json=json.dumps(tpl["graph"]),
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        status=0,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return ok(workflow_dict(w))


@router.put("/workflow")
def update_workflow(body: WorkflowUpdate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    w = db.get(Workflow, body.id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    if body.name is not None:
        w.name = body.name.strip()
    if body.desc is not None:
        w.desc = body.desc
    if body.graph is not None:
        snapshot_workflow_version(db, w, ctx.user.user_id)
        w.graph_json = json.dumps(body.graph)
    elif body.name is not None or body.desc is not None:
        snapshot_workflow_version(db, w, ctx.user.user_id)
    w.update_time = datetime.utcnow()
    db.commit()
    db.refresh(w)
    return ok(workflow_dict(w))


@router.post("/workflow/status")
def set_workflow_status(
    id: str = Body(..., alias="id"),
    status: int = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    w.status = status
    w.update_time = datetime.utcnow()
    if status == 1 and not getattr(w, "webhook_token", ""):
        w.webhook_token = secrets.token_urlsafe(24)
    db.commit()
    return ok({"id": w.id, "status": status, "webhook_token": getattr(w, "webhook_token", "") or ""})


@router.post("/workflow/delete")
def delete_workflow(
    workflow_id: str = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).delete()
    db.query(WorkflowSchedule).filter(WorkflowSchedule.workflow_id == workflow_id).delete()
    db.delete(w)
    db.commit()
    return ok(None)


@router.post("/workflow/run")
async def execute_workflow(
    body: WorkflowRunRequest,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, body.workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    result = await run_workflow(db, w, ctx.user.user_id, body.input.strip(), ctx.workspace_id)
    return ok(result)


@router.get("/workflow/online")
def online_workflows(
    limit: int = Query(50),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    rows = (
        db.query(Workflow)
        .filter(Workflow.workspace_id == ctx.workspace_id, Workflow.status == 1)
        .order_by(Workflow.update_time.desc())
        .limit(limit)
        .all()
    )
    return ok([workflow_dict(w) for w in rows])


@router.post("/workflow/webhook/{token}")
async def workflow_webhook(token: str, body: dict, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.webhook_token == token, Workflow.status == 1).first()
    if not w:
        return fail(404, "Invalid webhook")
    user_input = (body.get("input") or body.get("message") or body.get("text") or "").strip()
    if not user_input:
        return fail(400, "input required")
    result = await run_workflow(db, w, w.user_id, user_input, w.workspace_id)
    return ok(result)


@router.post("/workflow/resume")
async def resume_workflow(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    pending_id = body.get("pending_run_id")
    if not pending_id:
        return fail(400, "pending_run_id required")
    result = await resume_workflow_pending(
        db,
        int(pending_id),
        ctx.user.user_id,
        approved=bool(body.get("approved", True)),
        note=(body.get("note") or "").strip(),
        workspace_id=ctx.workspace_id,
    )
    return ok(result)


@router.get("/workflow/{workflow_id}/versions")
def workflow_versions(workflow_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    return ok(list_workflow_versions(db, workflow_id))


@router.post("/workflow/{workflow_id}/versions/{version_id}/restore")
def restore_version(
    workflow_id: str,
    version_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    data = restore_workflow_version(db, w, version_id, ctx.user.user_id)
    if not data:
        return fail(404, "Version not found")
    return ok(data)


@router.get("/workflow/{workflow_id}/schedules")
def list_workflow_schedules(
    workflow_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    rows = (
        db.query(WorkflowSchedule)
        .filter(WorkflowSchedule.workflow_id == workflow_id, WorkflowSchedule.workspace_id == ctx.workspace_id)
        .order_by(WorkflowSchedule.create_time.desc())
        .all()
    )
    return ok([schedule_dict(r) for r in rows])


@router.post("/workflow/{workflow_id}/schedules")
def create_workflow_schedule(
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    if w.status != 1:
        return fail(400, "Publish workflow before scheduling")
    try:
        cron_expr = validate_cron((body.get("cron_expression") or "").strip())
    except ValueError as exc:
        return fail(400, str(exc))
    now = datetime.utcnow()
    row = WorkflowSchedule(
        workflow_id=workflow_id,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        cron_expression=cron_expr,
        input_text=(body.get("input_text") or "Scheduled run").strip()[:2000],
        enabled=1 if body.get("enabled", True) else 0,
    )
    db.add(row)
    db.flush()
    row.next_run_at = compute_schedule_next_run(row, now)
    db.commit()
    db.refresh(row)
    return ok(schedule_dict(row))


@router.patch("/workflow/schedules/{schedule_id}")
def update_workflow_schedule(
    schedule_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = db.get(WorkflowSchedule, schedule_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Schedule not found")
    if "cron_expression" in body and body["cron_expression"]:
        try:
            row.cron_expression = validate_cron(str(body["cron_expression"]).strip())
        except ValueError as exc:
            return fail(400, str(exc))
    if "input_text" in body:
        row.input_text = str(body["input_text"] or "").strip()[:2000]
    if "enabled" in body:
        row.enabled = 1 if body["enabled"] else 0
    row.next_run_at = compute_schedule_next_run(row)
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok(schedule_dict(row))


@router.delete("/workflow/schedules/{schedule_id}")
def delete_workflow_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = db.get(WorkflowSchedule, schedule_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Schedule not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": schedule_id})
