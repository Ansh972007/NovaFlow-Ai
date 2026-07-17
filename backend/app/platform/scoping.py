"""Automatic tenant scoping — never hand-filter workspace_id in new code."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Query, Session

T = TypeVar("T")


def not_deleted(model: Any):
    """Filter soft-deleted rows when model has deleted_at."""
    if hasattr(model, "deleted_at"):
        return model.deleted_at.is_(None)
    return True


def scoped_query(db: Session, model: type[T], workspace_id: int) -> Query:
    """
    Return a query pre-filtered to the active workspace.

    Models MUST expose workspace_id. Soft-deleted rows are excluded when present.
    """
    if not hasattr(model, "workspace_id"):
        raise RuntimeError(f"{model.__name__} is not tenant-scoped (missing workspace_id)")
    q = db.query(model).filter(model.workspace_id == workspace_id)
    if hasattr(model, "deleted_at"):
        q = q.filter(model.deleted_at.is_(None))
    return q


def require_same_workspace(resource: Any, workspace_id: int, *, label: str = "Resource") -> None:
    if resource is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    wid = getattr(resource, "workspace_id", None)
    if wid is None or int(wid) != int(workspace_id):
        # Opaque 404 — do not leak cross-tenant existence
        raise HTTPException(status_code=404, detail=f"{label} not found")


def attach_tenant_fields(
    obj: Any,
    *,
    workspace_id: int,
    user_id: int | None = None,
    team_id: int | None = None,
) -> Any:
    """Set standard tenant columns on a new ORM object before flush."""
    if hasattr(obj, "workspace_id"):
        obj.workspace_id = workspace_id
    if team_id is not None and hasattr(obj, "team_id"):
        obj.team_id = team_id
    if user_id is not None:
        if hasattr(obj, "created_by") and getattr(obj, "created_by", None) is None:
            obj.created_by = user_id
        if hasattr(obj, "updated_by"):
            obj.updated_by = user_id
        if hasattr(obj, "user_id") and getattr(obj, "user_id", None) in (None, 0):
            obj.user_id = user_id
    return obj
