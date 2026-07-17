"""Tenant-bound execution for background workers, schedulers, and queues."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.platform.scoping import scoped_query
from app.security.audit import audit_log

_current_worker: ContextVar[Optional["WorkerTenantContext"]] = ContextVar(
    "novaflow_worker_tenant", default=None
)


@dataclass
class WorkerTenantContext:
    workspace_id: int
    user_id: Optional[int] = None
    team_id: Optional[int] = None
    source: str = "scheduler"
    job_type: str = ""
    job_id: str = ""

    def query(self, db: Session, model):
        return scoped_query(db, model, self.workspace_id)

    def audit(self, db: Session, action: str, **kwargs) -> None:
        audit_log(
            db,
            action=action,
            actor_user_id=self.user_id,
            workspace_id=self.workspace_id,
            detail={
                "source": self.source,
                "job_type": self.job_type,
                "job_id": self.job_id,
                **(kwargs.get("detail") or {}),
            },
            resource_type=kwargs.get("resource_type", ""),
            resource_id=kwargs.get("resource_id", ""),
            success=kwargs.get("success", True),
        )


def get_worker_tenant() -> Optional[WorkerTenantContext]:
    return _current_worker.get()


@contextmanager
def worker_tenant(
    workspace_id: int,
    *,
    user_id: int | None = None,
    team_id: int | None = None,
    source: str = "scheduler",
    job_type: str = "",
    job_id: str = "",
    db: Session | None = None,
) -> Iterator[WorkerTenantContext]:
    """Bind tenant context for the duration of a background job."""
    if not workspace_id:
        raise RuntimeError("Background job refused: missing workspace_id")
    ctx = WorkerTenantContext(
        workspace_id=int(workspace_id),
        user_id=user_id,
        team_id=team_id,
        source=source,
        job_type=job_type,
        job_id=str(job_id or ""),
    )
    token = _current_worker.set(ctx)
    try:
        if db is not None:
            ctx.audit(
                db,
                "worker.job.start",
                resource_type=job_type,
                resource_id=str(job_id or ""),
            )
        yield ctx
    finally:
        if db is not None:
            try:
                ctx.audit(
                    db,
                    "worker.job.end",
                    resource_type=job_type,
                    resource_id=str(job_id or ""),
                )
            except Exception:
                pass
        _current_worker.reset(token)


def require_worker_tenant() -> WorkerTenantContext:
    ctx = get_worker_tenant()
    if ctx is None:
        raise RuntimeError("Background job executing without WorkerTenantContext")
    return ctx


def tenant_cache_key(workspace_id: int, *parts: str) -> str:
    """Redis / cache key prefix — always tenant-scoped."""
    safe = [str(workspace_id)] + [str(p).replace(":", "_") for p in parts]
    return "nf:ws:" + ":".join(safe)


def tenant_rate_identity(workspace_id: int | None, identity: str) -> str:
    if workspace_id is None:
        return f"global:{identity}"
    return f"ws:{workspace_id}:{identity}"
