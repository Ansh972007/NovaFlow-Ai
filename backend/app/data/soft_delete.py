"""Global soft-delete operations — no hard delete by default."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.data.config import load_data_config
from app.security.audit import audit_log

T = TypeVar("T")


def soft_delete_row(
    db: Session,
    obj: Any,
    *,
    actor_user_id: int | None = None,
    workspace_id: int | None = None,
    force: bool = False,
) -> Any:
    if not hasattr(obj, "deleted_at"):
        raise HTTPException(status_code=400, detail="Resource does not support soft delete")
    if getattr(obj, "legal_hold", 0) and not force:
        raise HTTPException(status_code=403, detail="Resource is under legal hold")
    obj.deleted_at = datetime.utcnow()
    if hasattr(obj, "updated_by") and actor_user_id is not None:
        obj.updated_by = actor_user_id
    if hasattr(obj, "row_version") and obj.row_version is not None:
        obj.row_version = int(obj.row_version) + 1
    db.commit()
    audit_log(
        db,
        action="resource.soft_deleted",
        actor_user_id=actor_user_id,
        workspace_id=workspace_id or getattr(obj, "workspace_id", None),
        resource_type=type(obj).__name__,
        resource_id=str(getattr(obj, "id", "")),
    )
    return obj


def restore_row(
    db: Session,
    obj: Any,
    *,
    actor_user_id: int | None = None,
    workspace_id: int | None = None,
) -> Any:
    if not hasattr(obj, "deleted_at"):
        raise HTTPException(status_code=400, detail="Resource does not support restore")
    obj.deleted_at = None
    if hasattr(obj, "updated_by") and actor_user_id is not None:
        obj.updated_by = actor_user_id
    if hasattr(obj, "row_version") and obj.row_version is not None:
        obj.row_version = int(obj.row_version) + 1
    db.commit()
    audit_log(
        db,
        action="resource.restored",
        actor_user_id=actor_user_id,
        workspace_id=workspace_id or getattr(obj, "workspace_id", None),
        resource_type=type(obj).__name__,
        resource_id=str(getattr(obj, "id", "")),
    )
    return obj


def purge_permanently(
    db: Session,
    obj: Any,
    *,
    actor_user_id: int | None = None,
    workspace_id: int | None = None,
    confirm: bool = False,
) -> None:
    """Hard delete — only after soft-delete retention or explicit confirm."""
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true required for permanent delete")
    if getattr(obj, "legal_hold", 0):
        raise HTTPException(status_code=403, detail="Resource is under legal hold")
    cfg = load_data_config()
    deleted_at = getattr(obj, "deleted_at", None)
    if deleted_at is not None:
        earliest = datetime.utcnow() - timedelta(days=cfg.soft_delete_purge_days)
        if deleted_at > earliest:
            raise HTTPException(
                status_code=400,
                detail=f"Retention period not elapsed ({cfg.soft_delete_purge_days} days)",
            )
    rid = str(getattr(obj, "id", ""))
    rtype = type(obj).__name__
    wid = workspace_id or getattr(obj, "workspace_id", None)
    db.delete(obj)
    db.commit()
    audit_log(
        db,
        action="resource.purged",
        actor_user_id=actor_user_id,
        workspace_id=wid,
        resource_type=rtype,
        resource_id=rid,
        detail={"permanent": True},
    )


def not_deleted_filter(model: type[T]):
    if hasattr(model, "deleted_at"):
        return model.deleted_at.is_(None)
    return True
