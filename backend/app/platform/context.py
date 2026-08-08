"""TenantContext — request-scoped workspace + org + team binding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import (
    EmergencyAccessGrant,
    Organization,
    User,
    Workspace,
    WorkspaceMember,
    get_db,
)
from app.deps import get_current_user
from app.platform.roles import has_workspace_min_role, normalize_workspace_role
from app.platform.scoping import scoped_query
from app.security.audit import audit_log
from app.services.tenancy import ensure_personal_workspace, get_membership
from datetime import datetime

T = TypeVar("T")


@dataclass
class TenantContext:
    """Bound tenant for the current request. Prefer this over WorkspaceCtx for new code."""

    user: User
    workspace: Workspace
    workspace_id: int
    role: str
    organization_id: Optional[int] = None
    organization: Optional[Organization] = None
    team_id: Optional[int] = None
    via_emergency_access: bool = False
    emergency_grant_id: Optional[int] = None

    # Back-compat aliases used by existing routers expecting WorkspaceCtx
    @property
    def workspace_ctx_role(self) -> str:
        return self.role

    def query(self, db: Session, model: type[T]):
        return scoped_query(db, model, self.workspace_id)

    def require_role(self, min_role: str) -> None:
        if not has_workspace_min_role(self.role, min_role):
            raise HTTPException(
                status_code=403,
                detail=f"{normalize_workspace_role(min_role)} access required in this workspace",
            )


def _active_emergency_grant(db: Session, user_id: int, workspace_id: int) -> EmergencyAccessGrant | None:
    now = datetime.utcnow()
    try:
        return (
            db.query(EmergencyAccessGrant)
            .filter(
                EmergencyAccessGrant.grantee_user_id == user_id,
                EmergencyAccessGrant.workspace_id == workspace_id,
                EmergencyAccessGrant.status == "active",
                EmergencyAccessGrant.starts_at.isnot(None),
                EmergencyAccessGrant.starts_at <= now,
                EmergencyAccessGrant.ends_at.isnot(None),
                EmergencyAccessGrant.ends_at >= now,
            )
            .first()
        )
    except Exception:
        db.rollback()
        return None


def resolve_tenant(
    db: Session,
    user: User,
    *,
    workspace_id: int | None,
    team_id: int | None = None,
    request: Request | None = None,
) -> TenantContext:
    membership = None
    ws = None
    emergency = None

    if workspace_id:
        ws = db.get(Workspace, workspace_id)
        if ws and ws.deleted_at is None:
            membership = get_membership(db, user.user_id, workspace_id)
            if not membership:
                emergency = _active_emergency_grant(db, user.user_id, workspace_id)

    if not ws or ws.deleted_at is not None or (not membership and not emergency):
        ws = ensure_personal_workspace(db, user)
        workspace_id = ws.id
        membership = get_membership(db, user.user_id, workspace_id)
        emergency = None

    if membership:
        role = normalize_workspace_role(membership.role or "editor")
        if ws.owner_id == user.user_id:
            role = "owner"
    elif emergency:
        role = "viewer"  # break-glass is read-biased by default
        if request:
            audit_log(
                db,
                action="tenant.emergency_access.used",
                actor_user_id=user.user_id,
                workspace_id=ws.id,
                success=True,
                detail={"grant_id": emergency.id, "reason": emergency.reason},
                ip=request.client.host if request.client else "",
            )
    else:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    org = db.get(Organization, ws.organization_id) if ws.organization_id else None

    return TenantContext(
        user=user,
        workspace=ws,
        workspace_id=ws.id,
        role=role,
        organization_id=ws.organization_id,
        organization=org,
        team_id=team_id,
        via_emergency_access=bool(emergency),
        emergency_grant_id=emergency.id if emergency else None,
    )


def workspace_role_at_least_admin(role: str) -> bool:
    return has_workspace_min_role(role, "admin")


def get_tenant_context(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[int] = Header(None, alias="X-Workspace-Id"),
    workspace_id_q: Optional[int] = Query(None, alias="workspace_id"),
    x_team_id: Optional[int] = Header(None, alias="X-Team-Id"),
) -> TenantContext:
    wid = x_workspace_id or workspace_id_q
    return resolve_tenant(db, user, workspace_id=wid, team_id=x_team_id, request=request)


# Compatibility shim: existing code Depends(get_workspace_ctx) → WorkspaceCtx-like
def tenant_as_workspace_ctx(ctx: TenantContext = Depends(get_tenant_context)):
    from app.services.tenancy import WorkspaceCtx

    return WorkspaceCtx(
        user=ctx.user,
        workspace_id=ctx.workspace_id,
        role="admin" if ctx.role == "owner" else ctx.role if ctx.role in {"admin", "editor", "viewer"} else (
            "admin" if has_workspace_min_role(ctx.role, "admin") else
            "editor" if has_workspace_min_role(ctx.role, "editor") else "viewer"
        ),
        workspace=ctx.workspace,
    )
