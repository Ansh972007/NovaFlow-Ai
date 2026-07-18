import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowPresence, WorkflowPresenceSession, WorkflowRun, WorkflowSchedule, WorkflowVersion, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import WorkflowCreate, WorkflowRunRequest, WorkflowUpdate, fail, ok
from app.services.cron_schedule import validate_cron
from app.services.workflow import (
    TEMPLATES,
    get_workflow_version,
    list_workflow_versions,
    restore_workflow_version,
    resume_workflow_pending,
    run_workflow,
    snapshot_workflow_version,
    workflow_dict,
)
from app.services.workflow_diff import diff_workflow_graphs, format_diff_markdown
from app.services.workflow_scheduler import compute_schedule_next_run, run_schedule_now, schedule_dict

router = APIRouter(tags=["Workflow"])


@router.get("/workflow/schedules")
def list_workspace_schedules(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(WorkflowSchedule)
        
        .order_by(WorkflowSchedule.create_time.desc())
        .all()
    )
    out = []
    for row in rows:
        wf = db.get(Workflow, row.workflow_id)
        out.append(schedule_dict(row, wf.name if wf else None))
    return ok(out)


@router.post("/workflow/schedules/{schedule_id}/trigger")
async def trigger_workspace_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    try:
        return ok(await run_schedule_now(db, schedule_id, ctx.workspace_id))
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/workflow/runs")
def list_workspace_runs(
    limit: int = Query(50, ge=1, le=100),
    workflow_id: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = ctx.query(WorkflowRun)
    if workflow_id:
        q = q.filter(WorkflowRun.workflow_id == workflow_id)
    rows = q.order_by(WorkflowRun.create_time.desc()).limit(limit).all()
    out = []
    for r in rows:
        wf = db.get(Workflow, r.workflow_id)
        try:
            steps = json.loads(r.steps_json or "[]")
            step_count = len(steps) if isinstance(steps, list) else 0
        except json.JSONDecodeError:
            step_count = 0
        status_code = int(r.status or 1)
        out.append(
            {
                "id": r.id,
                "workflow_id": r.workflow_id,
                "workflow_name": wf.name if wf else r.workflow_id,
                "input": (r.input_text or "")[:200],
                "output": (r.output_text or "")[:200],
                "duration_ms": r.duration_ms,
                "status": status_code,
                "status_label": "error" if status_code == 2 else "completed",
                "step_count": step_count,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
        )
    return ok(out)


@router.get("/workflow/runs/{run_id}")
def get_workflow_run(run_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    run = ctx.fetch(WorkflowRun, run_id)
    if not run:
        return fail(404, "Run not found")
    try:
        steps = json.loads(run.steps_json or "[]")
    except json.JSONDecodeError:
        steps = []
    wf = db.get(Workflow, run.workflow_id)
    status_code = int(run.status or 1)
    return ok(
        {
            "id": run.id,
            "workflow_id": run.workflow_id,
            "workflow_name": wf.name if wf else run.workflow_id,
            "input": run.input_text or "",
            "output": run.output_text or "",
            "duration_ms": run.duration_ms,
            "status": status_code,
            "status_label": "error" if status_code == 2 else "completed",
            "create_time": run.create_time.isoformat() if run.create_time else None,
            "steps": steps if isinstance(steps, list) else [],
        }
    )


@router.get("/workflow")
def list_workflows(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = ctx.query(Workflow)
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
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
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
            "step_count": len(json.loads(r.steps_json or "[]")) if r.steps_json else 0,
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
    w = ctx.fetch(Workflow, body.id)
    if not w:
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
    if hasattr(body, "run_webhook_url") and body.run_webhook_url is not None:
        w.run_webhook_url = str(body.run_webhook_url or "").strip()[:500]
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
    w = ctx.fetch(Workflow, id)
    if not w:
        return fail(404, "Workflow not found")
    if status == 1:
        from app.workflow_intelligence.graph.parser import parse_graph
        from app.workflow_intelligence.publish_gate import check_publish_ready

        gate = check_publish_ready(parse_graph(w.graph_json))
        if not gate.get("ready"):
            return fail(
                400,
                "Workflow failed publish validation",
                data={"publish_gate": gate},
            )
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
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
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
    w = ctx.fetch(Workflow, body.workflow_id)
    if not w:
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
        ctx.query(Workflow)
        .filter(Workflow.status == 1)
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


@router.get("/workflow/{workflow_id}/versions/diff")
def workflow_version_diff(
    workflow_id: str,
    from_id: int = Query(...),
    to_id: str = Query("current"),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    old_v = get_workflow_version(db, workflow_id, from_id)
    if not old_v:
        return fail(404, "From version not found")
    if to_id == "current":
        try:
            new_graph = json.loads(w.graph_json or "{}")
        except json.JSONDecodeError:
            new_graph = {"nodes": [], "edges": []}
        to_label = "current"
    else:
        new_v = get_workflow_version(db, workflow_id, int(to_id))
        if not new_v:
            return fail(404, "To version not found")
        new_graph = new_v["graph"]
        to_label = f"v{new_v['version_no']}"
    diff = diff_workflow_graphs(old_v["graph"], new_graph)
    return ok({
        "from": f"v{old_v['version_no']}",
        "to": to_label,
        "from_graph": old_v["graph"],
        "to_graph": new_graph,
        **diff,
    })


@router.get("/workflow/{workflow_id}/versions/diff/export")
def workflow_version_diff_export(
    workflow_id: str,
    from_id: int = Query(...),
    to_id: str = Query("current"),
    format: str = Query("json", pattern="^(json|md)$"),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    old_v = get_workflow_version(db, workflow_id, from_id)
    if not old_v:
        return fail(404, "From version not found")
    if to_id == "current":
        try:
            new_graph = json.loads(w.graph_json or "{}")
        except json.JSONDecodeError:
            new_graph = {"nodes": [], "edges": []}
        to_label = "current"
    else:
        new_v = get_workflow_version(db, workflow_id, int(to_id))
        if not new_v:
            return fail(404, "To version not found")
        new_graph = new_v["graph"]
        to_label = f"v{new_v['version_no']}"
    diff = diff_workflow_graphs(old_v["graph"], new_graph)
    from_label = f"v{old_v['version_no']}"
    payload = {
        "workflow_id": workflow_id,
        "workflow_name": w.name,
        "from": from_label,
        "to": to_label,
        **diff,
    }
    safe_name = (w.name or "workflow").replace(" ", "-")[:40]
    filename_base = f"novaflow-diff-{safe_name}-{from_label}-to-{to_label}".replace("/", "-")

    if format == "md":
        body = format_diff_markdown(
            diff,
            workflow_name=w.name or "Workflow",
            from_label=from_label,
            to_label=to_label,
        )
        return PlainTextResponse(
            body,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
        )

    return JSONResponse(
        payload,
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
    )


@router.get("/workflow/{workflow_id}/versions/{version_id}")
def workflow_version_detail(
    workflow_id: str,
    version_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    data = get_workflow_version(db, workflow_id, version_id)
    if not data:
        return fail(404, "Version not found")
    return ok(data)


@router.post("/workflow/{workflow_id}/presence")
def touch_workflow_presence(
    workflow_id: str,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    now = datetime.utcnow()
    row = (
        db.query(WorkflowPresenceSession)
        .filter(
            WorkflowPresenceSession.workflow_id == workflow_id,
            WorkflowPresenceSession.user_id == ctx.user.user_id,
        )
        .first()
    )
    if row:
        row.user_name = ctx.user.user_name
        row.updated_at = now
        if "cursor_x" in body:
            row.cursor_x = float(body.get("cursor_x") or 0)
        if "cursor_y" in body:
            row.cursor_y = float(body.get("cursor_y") or 0)
        if "selected_id" in body:
            row.selected_id = str(body.get("selected_id") or "")[:64]
    else:
        row = WorkflowPresenceSession(
            workflow_id=workflow_id,
            user_id=ctx.user.user_id,
            user_name=ctx.user.user_name,
            cursor_x=float(body.get("cursor_x") or 0),
            cursor_y=float(body.get("cursor_y") or 0),
            selected_id=str(body.get("selected_id") or "")[:64],
            updated_at=now,
        )
        db.add(row)
    legacy = db.get(WorkflowPresence, workflow_id)
    if legacy:
        legacy.user_id = ctx.user.user_id
        legacy.user_name = ctx.user.user_name
        legacy.updated_at = now
    else:
        db.add(
            WorkflowPresence(
                workflow_id=workflow_id,
                user_id=ctx.user.user_id,
                user_name=ctx.user.user_name,
                updated_at=now,
            )
        )
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        return ok({"workflow_id": workflow_id, "user_name": ctx.user.user_name, "presence_degraded": True})
    return ok({"workflow_id": workflow_id, "user_name": ctx.user.user_name})


@router.get("/workflow/{workflow_id}/presence")
def get_workflow_presence(
    workflow_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    cutoff = datetime.utcnow()
    rows = (
        db.query(WorkflowPresenceSession)
        .filter(WorkflowPresenceSession.workflow_id == workflow_id)
        .all()
    )
    viewers = []
    for row in rows:
        age = (cutoff - row.updated_at).total_seconds() if row.updated_at else 9999
        if age > 45:
            continue
        viewers.append(
            {
                "user_id": row.user_id,
                "user_name": row.user_name,
                "is_self": row.user_id == ctx.user.user_id,
                "cursor_x": row.cursor_x or 0,
                "cursor_y": row.cursor_y or 0,
                "selected_id": row.selected_id or "",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    others = [v for v in viewers if not v["is_self"]]
    primary = others[0] if others else None
    return ok({"viewers": viewers, "primary": primary})


@router.get("/workflow/{workflow_id}/versions")
def workflow_versions(workflow_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    return ok(list_workflow_versions(db, workflow_id))


@router.post("/workflow/{workflow_id}/versions/{version_id}/restore")
def restore_version(
    workflow_id: str,
    version_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
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
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    rows = (
        ctx.query(WorkflowSchedule)
        .filter(WorkflowSchedule.workflow_id == workflow_id)
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
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
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
    row = ctx.fetch(WorkflowSchedule, schedule_id)
    if not row:
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
    row = ctx.fetch(WorkflowSchedule, schedule_id)
    if not row:
        return fail(404, "Schedule not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": schedule_id})
