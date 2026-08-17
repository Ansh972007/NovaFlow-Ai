import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowComment, WorkflowRating, get_db
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


def _comment_counts(db: Session, workflow_ids: list[str]) -> dict[str, int]:
    if not workflow_ids:
        return {}
    rows = (
        db.query(WorkflowComment.workflow_id, func.count(WorkflowComment.id))
        .filter(WorkflowComment.workflow_id.in_(workflow_ids))
        .group_by(WorkflowComment.workflow_id)
        .all()
    )
    return {wid: int(cnt) for wid, cnt in rows}


@router.get("/marketplace/workflows")
def list_marketplace_workflows(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    rows = (
        db.query(Workflow)
        .filter(Workflow.is_public == 1)
        .order_by(Workflow.update_time.desc())
        .limit(limit)
        .all()
    )
    items = []
    ids = [w.id for w in rows]
    stats = _rating_stats(db, ids)
    mine = _user_ratings(db, ids, ctx.user.user_id)
    comments = _comment_counts(db, ids)
    for w in rows:
        d = workflow_dict(w)
        d["from_workspace"] = w.workspace_id != ctx.workspace_id
        d.update(stats.get(w.id, {"avg_rating": 0, "rating_count": 0}))
        d["user_rating"] = mine.get(w.id)
        d["comment_count"] = comments.get(w.id, 0)
        items.append(d)
    return ok({"items": items, "templates": [{"id": k, **{kk: v for kk, v in tpl.items() if kk != "graph"}} for k, tpl in TEMPLATES.items()]})


@router.post("/marketplace/workflows/{workflow_id}/clone")
def clone_marketplace_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    src = db.get(Workflow, workflow_id)
    if not src or not src.is_public:
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
    w = ctx.fetch(Workflow, workflow_id)
    if not w:
        return fail(404, "Workflow not found")
    is_pub = 1 if body.get("is_public") else 0
    w.is_public = is_pub
    if is_pub:
        w.status = 1
    db.commit()
    db.refresh(w)
    return ok({"id": w.id, "is_public": w.is_public, "status": w.status})


@router.post("/marketplace/workflows/{workflow_id}/rate")
def rate_marketplace_workflow(
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or not w.is_public:
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


@router.get("/marketplace/workflows/{workflow_id}/comments")
def list_workflow_comments(
    workflow_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    w = db.get(Workflow, workflow_id)
    if not w or not w.is_public:
        return fail(404, "Public workflow not found")
    rows = (
        db.query(WorkflowComment)
        .filter(WorkflowComment.workflow_id == workflow_id)
        .order_by(WorkflowComment.create_time.desc())
        .limit(limit)
        .all()
    )
    return ok(
        [
            {
                "id": c.id,
                "body": c.body,
                "user_name": c.user_name or "User",
                "create_time": c.create_time.isoformat() if c.create_time else None,
                "is_mine": c.user_id == ctx.user.user_id,
            }
            for c in rows
        ]
    )


@router.post("/marketplace/workflows/{workflow_id}/comments")
def post_workflow_comment(
    workflow_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    w = db.get(Workflow, workflow_id)
    if not w or not w.is_public:
        return fail(404, "Public workflow not found")
    text = (body.get("body") or "").strip()
    if not text:
        return fail(400, "body required")
    row = WorkflowComment(
        workflow_id=workflow_id,
        user_id=ctx.user.user_id,
        user_name=ctx.user.user_name,
        workspace_id=ctx.workspace_id,
        body=text[:1000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(
        {
            "id": row.id,
            "body": row.body,
            "user_name": row.user_name,
            "create_time": row.create_time.isoformat() if row.create_time else None,
            "is_mine": True,
        }
    )
