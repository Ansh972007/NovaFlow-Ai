"""RuntimeContext — binds PlatformContext to AI execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.orm import Session

from app.platform.permissions import workspace_has_permission
from app.security.rbac import Permission

if TYPE_CHECKING:
    from app.platform.access import PlatformContext


@dataclass
class RuntimeContext:
    """Tenant-bound AI execution context. Always derived from PlatformContext."""

    db: Session
    workspace_id: int
    user_id: int
    role: str
    platform: Optional["PlatformContext"] = None
    team_id: Optional[int] = None
    organization_id: Optional[int] = None
    via_emergency_access: bool = False
    cancel_event: Optional[asyncio.Event] = None
    session_id: str = ""
    trace_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:16])
    conversation_api_key: Optional[str] = None

    @classmethod
    def from_platform(cls, ctx: "PlatformContext", *, cancel_event: asyncio.Event | None = None) -> "RuntimeContext":
        return cls(
            db=ctx.db,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.user_id,
            role=ctx.role,
            platform=ctx,
            team_id=ctx.team_id,
            organization_id=ctx.organization_id,
            via_emergency_access=ctx.via_emergency_access,
            cancel_event=cancel_event,
        )

    @classmethod
    def from_ws(
        cls,
        db: Session,
        *,
        user_id: int,
        workspace_id: int,
        role: str,
        cancel_event: asyncio.Event | None = None,
    ) -> "RuntimeContext":
        """WebSocket path — tenant already resolved via resolve_tenant."""
        return cls(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            cancel_event=cancel_event,
        )

    def require_permission(self, permission: Permission | str) -> None:
        if self.platform is not None:
            self.platform.require(permission)
            return
        if not workspace_has_permission(
            self.role, permission, via_emergency_access=self.via_emergency_access
        ):
            perm = Permission(permission) if isinstance(permission, str) else permission
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail=f"Permission denied: {perm.value}")

    def audit(self, action: str, **kwargs: Any) -> None:
        if self.platform is not None:
            self.platform.audit(action, **kwargs)
            return
        from app.security.audit import audit_log

        audit_log(
            self.db,
            action=action,
            actor_user_id=self.user_id,
            workspace_id=self.workspace_id,
            detail=kwargs.get("detail") or {},
            resource_type=kwargs.get("resource_type", ""),
            resource_id=str(kwargs.get("resource_id", "")),
        )

    def cancelled(self) -> bool:
        return self.cancel_event is not None and self.cancel_event.is_set()


def runtime_from_platform(ctx: "PlatformContext", **kwargs: Any) -> RuntimeContext:
    return RuntimeContext.from_platform(ctx, **kwargs)
