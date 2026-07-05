import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowRating, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.workflow import TEMPLATES, workflow_dict

router = APIRouter(tags=["Marketplace"])


def _rating_stats(db: Session, workflow_ids: list[str]) -> dict[str, dict]:
    if not workflow_ids:
        return {}
    rows = (
        db.query(
            WorkflowRating.workflow_id,
            func.avg(WorkflowRating.score),
            func.count(WorkflowRating.id),
        )
        .filter(WorkflowRating.workflow_id.in_(workflow_ids))
        .group_by(WorkflowRating.workflow_id)
        .all()
    )
    return {
        wid: {"avg_rating": round(float(avg or 0), 1), "rating_count": int(cnt or 0)}
        for wid, avg, cnt in rows
    }


def _user_ratings(db: Session, workflow_ids: list[str], user_id: int) -> dict[str, int]:
    if not workflow_ids:
        return {}
    rows = (
        db.query(WorkflowRating.workflow_id, WorkflowRating.score)
        .filter(WorkflowRating.workflow_id.in_(workflow_ids), WorkflowRating.user_id == user_id)
        .all()
    )
    return {wid: score for wid, score in rows}


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
    ids = [w.id for w in rows]
    stats = _rating_stats(db, ids)
    mine = _user_ratings(db, ids, ctx.user.user_id)
    for w in rows:
        d = workflow_dict(w)
        d["from_workspace"] = w.workspace_id != ctx.workspace_id
        d.update(stats.get(w.id, {"avg_rating": 0, "rating_count": 0}))
        d["user_rating"] = mine.get(w.id)
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


@router.post("/marketplace/workflows/{workflow_id}/rate")
def rate_marketplace_workflow(
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or not w.is_public or w.status != 1:
        return fail(404, "Public workflow not found")
    score = int(body.get("score") or 0)
    if score < 1 or score > 5:
        return fail(400, "score must be 1–5")
    comment = (body.get("comment") or "").strip()[:500]
    existing = (
        db.query(WorkflowRating)
        .filter(WorkflowRating.workflow_id == workflow_id, WorkflowRating.user_id == ctx.user.user_id)
        .first()
    )
    if existing:
        existing.score = score
        existing.comment = comment
    else:
        db.add(
            WorkflowRating(
                workflow_id=workflow_id,
                user_id=ctx.user.user_id,
                workspace_id=ctx.workspace_id,
                score=score,
                comment=comment,
            )
        )
    db.commit()
    stats = _rating_stats(db, [workflow_id]).get(workflow_id, {"avg_rating": score, "rating_count": 1})
    return ok({"score": score, **stats})
