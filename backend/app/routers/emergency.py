"""Emergency access APIs — platform staff break-glass only."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin, require_min_role
from app.platform.emergency import (
    approve_emergency_access,
    deny_emergency_access,
    grant_dict,
    list_grants,
    request_emergency_access,
    revoke_emergency_access,
)
from app.schemas import fail, ok
from app.security.rbac import normalize_role

router = APIRouter(tags=["EmergencyAccess"])

require_super_admin = require_min_role("super_admin")


@router.post("/emergency-access/request")
def api_request_access(
    body: dict,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    try:
        row = request_emergency_access(
            db,
            requester=user,
            workspace_id=int(body.get("workspace_id") or 0),
            reason=body.get("reason") or "",
            duration_hours=float(body.get("duration_hours") or 1),
        )
    except (ValueError, TypeError) as exc:
        return fail(400, str(exc))
    return ok(grant_dict(row))


@router.post("/emergency-access/{grant_id}/approve")
def api_approve(
    grant_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_super_admin),
):
    body = body or {}
    try:
        row = approve_emergency_access(
            db,
            grant_id=grant_id,
            approver=user,
            duration_hours=float(body.get("duration_hours") or 1),
        )
    except ValueError as exc:
        return fail(400, str(exc))
    return ok(grant_dict(row))


@router.post("/emergency-access/{grant_id}/deny")
def api_deny(
    grant_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_super_admin),
):
    try:
        row = deny_emergency_access(db, grant_id=grant_id, actor=user)
    except ValueError as exc:
        return fail(400, str(exc))
    return ok(grant_dict(row))


@router.post("/emergency-access/{grant_id}/revoke")
def api_revoke(
    grant_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        row = revoke_emergency_access(db, grant_id=grant_id, actor=user)
    except ValueError as exc:
        return fail(400, str(exc))
    return ok(grant_dict(row))


@router.get("/emergency-access")
def api_list(
    workspace_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    role = normalize_role(user.role, user_id=user.user_id)
    if role != "super_admin":
        # Non-super platform admins only see their own requests
        rows = [
            g
            for g in list_grants(db, workspace_id=workspace_id, status=status, limit=200)
            if g.grantee_user_id == user.user_id
        ]
    else:
        rows = list_grants(db, workspace_id=workspace_id, status=status, limit=200)
    return ok([grant_dict(r) for r in rows])


@router.get("/emergency-access/active-banner")
def api_active_banner(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Customer-visible banner when break-glass is active on their workspace."""
    from app.database import EmergencyAccessGrant, WorkspaceMember
    from datetime import datetime

    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.user_id,
        )
        .first()
    )
    role = normalize_role(user.role, user_id=user.user_id)
    if not member and role != "super_admin":
        return fail(403, "Not a member of this workspace")

    now = datetime.utcnow()
    row = (
        db.query(EmergencyAccessGrant)
        .filter(
            EmergencyAccessGrant.workspace_id == workspace_id,
            EmergencyAccessGrant.status == "active",
            EmergencyAccessGrant.ends_at.isnot(None),
            EmergencyAccessGrant.ends_at >= now,
        )
        .order_by(EmergencyAccessGrant.ends_at.desc())
        .first()
    )
    if not row:
        return ok({"active": False})
    return ok(
        {
            "active": True,
            "read_only": True,
            "grant_id": row.id,
            "reason": row.reason,
            "ends_at": row.ends_at.isoformat() + "Z" if row.ends_at else None,
            "message": "Platform support has temporary read-only emergency access to this workspace.",
        }
    )
