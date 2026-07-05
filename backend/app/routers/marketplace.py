import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import Workflow, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.workflow import TEMPLATES, workflow_dict

router = APIRouter(tags=["Marketplace"])


@router.get("/marketplace/workflows")
def list_marketplace_workflows(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    rows = (
        db.query(Workflow)
        .filter(Workflow.is_public == 1, Workflow.status == 1)
        .order_by(Workflow.update_time.desc())
        .limit(limit)
        .all()
    )
    items = []
    for w in rows:
        d = workflow_dict(w)
        d["from_workspace"] = w.workspace_id != ctx.workspace_id
        items.append(d)
    return ok({"items": items, "templates": [{"id": k, **{kk: v for kk, v in tpl.items() if kk != "graph"}} for k, tpl in TEMPLATES.items()]})


@router.post("/marketplace/workflows/{workflow_id}/clone")
def clone_marketplace_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    src = db.get(Workflow, workflow_id)
    if not src or not src.is_public or src.status != 1:
        return fail(404, "Public workflow not found")
    clone = Workflow(
        name=f"{src.name} (copy)",
        desc=src.desc or "",
        graph_json=src.graph_json,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        status=0,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return ok(workflow_dict(clone))


@router.post("/workflow/{workflow_id}/share")
def share_workflow(
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or w.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    w.is_public = 1 if body.get("is_public") else 0
    db.commit()
    return ok({"id": w.id, "is_public": w.is_public})
