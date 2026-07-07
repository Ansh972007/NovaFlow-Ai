from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import DevProject, Workflow, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.projects import create_project, project_dict, update_project
from app.services.workflow import run_workflow, workflow_dict

router = APIRouter(tags=["Projects"])


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(DevProject)
        .filter(DevProject.workspace_id == ctx.workspace_id)
        .order_by(DevProject.update_time.desc())
        .all()
    )
    return ok([project_dict(r) for r in rows])


@router.post("/projects")
def create_project_route(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "Name required")
    row = create_project(
        db,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        name=name,
        description=(body.get("description") or "").strip(),
        integrations=body.get("integrations") if isinstance(body.get("integrations"), dict) else {},
        workflow_ids=body.get("workflow_ids") if isinstance(body.get("workflow_ids"), list) else [],
    )
    return ok(project_dict(row))


@router.patch("/projects/{project_id}")
def patch_project(
    project_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = db.get(DevProject, project_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Project not found")
    row = update_project(db, row, body)
    return ok(project_dict(row))


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = db.get(DevProject, project_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Project not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": project_id})


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    row = db.get(DevProject, project_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Project not found")
    payload = project_dict(row)
    workflows = []
    for wid in payload.get("workflow_ids") or []:
        wf = db.get(Workflow, str(wid))
        if wf and wf.workspace_id == ctx.workspace_id:
            workflows.append(workflow_dict(wf))
    payload["workflows"] = workflows
    return ok(payload)


@router.post("/projects/{project_id}/run/{workflow_id}")
async def run_project_workflow(
    project_id: int,
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = db.get(DevProject, project_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Project not found")
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    user_input = (body.get("input") or body.get("message") or "").strip()
    if not user_input:
        return fail(400, "input required")
    integrations = project_dict(row).get("integrations") or {}
    extra = {"chat_id": (body.get("chat_id") or integrations.get("telegram_chat_id") or "").strip()}
    result = await run_workflow(db, wf, ctx.user.user_id, user_input, ctx.workspace_id, extra_context=extra)
    return ok(result)
