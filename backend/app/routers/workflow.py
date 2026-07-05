import json
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowRun, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import WorkflowCreate, WorkflowRunRequest, WorkflowUpdate, fail, ok
from app.services.workflow import (
    TEMPLATES,
    run_workflow,
    workflow_dict,
)

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
        w.graph_json = json.dumps(body.graph)
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
    db.commit()
    return ok(None)


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
