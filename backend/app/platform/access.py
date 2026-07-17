"""PlatformContext — unified Tenant + Permission + Ownership + Audit surface.

Routers and services MUST use this instead of hand-filtering workspace_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar

from fastapi import HTTPException, Request
from sqlalchemy.orm import Query as SAQuery, Session

from app.database import Organization, User, Workspace
from app.platform.permissions import (
    require_workspace_permission,
    workspace_has_permission,
)
from app.platform.roles import has_workspace_min_role, normalize_workspace_role
from app.platform.scoping import attach_tenant_fields, scoped_query
from app.security.audit import audit_log
from app.security.rbac import Permission

T = TypeVar("T")


@dataclass
class PlatformContext:
    """Bound request context. Prefer over WorkspaceCtx for all new code."""

    user: User
    workspace: Workspace
    workspace_id: int
    role: str
    db: Session
    organization_id: Optional[int] = None
    organization: Optional[Organization] = None
    team_id: Optional[int] = None
    via_emergency_access: bool = False
    emergency_grant_id: Optional[int] = None
    request: Optional[Request] = None
    _audit_ip: str = field(default="", repr=False)
    _audit_ua: str = field(default="", repr=False)

    # --- Tenant scoping ---

    def query(self, model: type[T]) -> SAQuery:
        return scoped_query(self.db, model, self.workspace_id)

    def get(self, model: type[T], resource_id: Any, *, label: str | None = None) -> T:
        """Load a tenant resource by primary key with opaque cross-tenant 404."""
        name = label or getattr(model, "__name__", "Resource")
        obj = self.fetch(model, resource_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{name} not found")
        return obj

    def fetch(self, model: type[T], resource_id: Any) -> T | None:
        """Like get() but returns None instead of raising (for fail() style routers)."""
        obj = self.db.get(model, resource_id)
        if obj is None:
            return None
        wid = getattr(obj, "workspace_id", None)
        if wid is None or int(wid) != int(self.workspace_id):
            return None
        if hasattr(obj, "deleted_at") and getattr(obj, "deleted_at", None) is not None:
            return None
        return obj

    def attach(self, obj: Any, *, team_id: int | None = None) -> Any:
        return attach_tenant_fields(
            obj,
            workspace_id=self.workspace_id,
            user_id=self.user.user_id,
            team_id=team_id if team_id is not None else self.team_id,
        )

    # --- Permissions ---

    def can(self, permission: Permission | str) -> bool:
        return workspace_has_permission(
            self.role,
            permission,
            via_emergency_access=self.via_emergency_access,
        )

    def require(self, permission: Permission | str) -> None:
        require_workspace_permission(
            self.role,
            permission,
            via_emergency_access=self.via_emergency_access,
        )

    def require_min_role(self, min_role: str) -> None:
        if self.via_emergency_access and not has_workspace_min_role(min_role, "viewer"):
            # emergency is viewer-ceiling for write roles
            if has_workspace_min_role(min_role, "editor"):
                raise HTTPException(status_code=403, detail="Emergency access is read-only")
        if not has_workspace_min_role(self.role, min_role):
            raise HTTPException(
                status_code=403,
                detail=f"{normalize_workspace_role(min_role)} access required in this workspace",
            )

    # --- Ownership / visibility helpers ---

    def owns(self, resource: Any) -> bool:
        for attr in ("owner_id", "user_id", "created_by"):
            val = getattr(resource, attr, None)
            if val is not None and int(val) == int(self.user.user_id):
                return True
        return False

    def require_owner_or(self, resource: Any, min_role: str = "admin") -> None:
        if self.owns(resource) or has_workspace_min_role(self.role, min_role):
            return
        raise HTTPException(status_code=403, detail="Owner or elevated role required")

    # --- Audit ---

    def audit(
        self,
        action: str,
        *,
        resource_type: str = "",
        resource_id: str = "",
        success: bool = True,
        detail: dict | None = None,
    ) -> None:
        audit_log(
            self.db,
            action=action,
            actor_user_id=self.user.user_id,
            workspace_id=self.workspace_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else "",
            ip=self._audit_ip,
            user_agent=self._audit_ua,
            success=success,
            detail={
                **(detail or {}),
                "role": self.role,
                "via_emergency_access": self.via_emergency_access,
                "emergency_grant_id": self.emergency_grant_id,
            },
        )


def build_platform_context(
    db: Session,
    user: User,
    *,
    workspace_id: int | None,
    team_id: int | None = None,
    request: Request | None = None,
) -> PlatformContext:
    from app.platform.context import resolve_tenant

    tenant = resolve_tenant(db, user, workspace_id=workspace_id, team_id=team_id, request=request)
    ip = ""
    ua = ""
    if request is not None:
        ip = request.client.host if request.client else ""
        ua = (request.headers.get("user-agent") or "")[:512]
    return PlatformContext(
        user=tenant.user,
        workspace=tenant.workspace,
        workspace_id=tenant.workspace_id,
        role=tenant.role,
        db=db,
        organization_id=tenant.organization_id,
        organization=tenant.organization,
        team_id=tenant.team_id,
        via_emergency_access=tenant.via_emergency_access,
        emergency_grant_id=tenant.emergency_grant_id,
        request=request,
        _audit_ip=ip,
        _audit_ua=ua,
    )


# FastAPI Depends live in app.deps (get_platform_ctx / require_permission)
# to avoid circular imports with authentication.