"""Node library API — workspace-scoped declarative API nodes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_workspace_ctx, require_workspace_admin, require_workspace_editor
from app.schemas import fail, ok
from app.services.node_library import (
    check_probe_rate,
    create_definition,
    deprecate_definition,
    get_definition,
    list_library,
    node_def_dict,
    probe_http,
    publish_definition,
    test_definition,
    update_definition,
)

router = APIRouter(tags=["NodeLibrary"])


@router.get("/nodes/library")
def api_list_library(
    include_drafts: bool = True,
    status: str | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    return ok(
        list_library(
            db,
            ctx.workspace_id,
            include_drafts=include_drafts,
            status=status,
        )
    )


@router.get("/nodes/library/{def_id}")
def api_get_definition(
    def_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    row = get_definition(db, ctx.workspace_id, def_id)
    if not row:
        return fail(404, "Node definition not found")
    return ok(node_def_dict(row))


@router.post("/nodes/library")
def api_create_definition(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    try:
        row = create_definition(db, ctx.workspace_id, ctx.user.user_id, body)
        ctx.audit(
            "node_library.create",
            resource_type="node_definition",
            resource_id=row.id,
            detail={"slug": row.slug},
        )
        return ok(node_def_dict(row))
    except ValueError as exc:
        return fail(400, str(exc))


@router.patch("/nodes/library/{def_id}")
def api_update_definition(
    def_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    try:
        row = update_definition(db, ctx.workspace_id, def_id, body)
        ctx.audit("node_library.update", resource_type="node_definition", resource_id=row.id)
        return ok(node_def_dict(row))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/nodes/library/probe")
async def api_probe_http(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    if not check_probe_rate(ctx.workspace_id, ctx.user.user_id):
        return fail(429, "Probe rate limit exceeded — try again in a minute")
    result = await probe_http(db, ctx.workspace_id, body)
    return ok(result)


@router.post("/nodes/library/{def_id}/test")
async def api_test_definition(
    def_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    try:
        result = await test_definition(
            db,
            ctx.workspace_id,
            def_id,
            sample_context=body.get("context"),
        )
        return ok(result)
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/nodes/library/{def_id}/publish")
def api_publish_definition(
    def_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    try:
        row = publish_definition(
            db,
            ctx.workspace_id,
            ctx.user.user_id,
            def_id,
            require_test=bool(body.get("require_test", True)),
        )
        return ok(node_def_dict(row))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/nodes/library/{def_id}/deprecate")
def api_deprecate_definition(
    def_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    try:
        row = deprecate_definition(db, ctx.workspace_id, ctx.user.user_id, def_id)
        return ok(node_def_dict(row))
    except ValueError as exc:
        return fail(400, str(exc))
