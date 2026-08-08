"""Emergency (break-glass) access to customer workspaces.

Platform staff never auto-access tenant data. Access requires:
request → approval → time-boxed active grant → auto-expiry → audit.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import EmergencyAccessGrant, User, Workspace
from app.security.audit import audit_log
from app.security.rbac import has_min_role, normalize_role

MAX_DURATION_HOURS = 8
DEFAULT_DURATION_HOURS = 1


def _assert_platform_staff(user: User) -> None:
    role = normalize_role(user.role, user_id=user.user_id)
    if not has_min_role(role, "admin", user_id=user.user_id):
        # Only platform-level admins / support may request break-glass
        if role not in ("super_admin", "admin"):
            raise ValueError("Only platform staff may request emergency access")


def request_emergency_access(
    db: Session,
    *,
    requester: User,
    workspace_id: int,
    reason: str,
    duration_hours: float = DEFAULT_DURATION_HOURS,
) -> EmergencyAccessGrant:
    _assert_platform_staff(requester)
    reason_n = (reason or "").strip()
    if len(reason_n) < 10:
        raise ValueError("Reason must be at least 10 characters")
    hours = max(0.25, min(float(duration_hours or DEFAULT_DURATION_HOURS), MAX_DURATION_HOURS))
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is not None:
        raise ValueError("Workspace not found")

    row = EmergencyAccessGrant(
        workspace_id=workspace_id,
        grantee_user_id=requester.user_id,
        reason=reason_n[:500],
        status="pending",
        starts_at=None,
        ends_at=None,
        create_time=datetime.utcnow(),
    )
    # Store requested duration in reason audit detail via separate field — encode ends tentatively
    db.add(row)
    db.commit()
    db.refresh(row)
    audit_log(
        db,
        action="emergency_access.requested",
        actor_user_id=requester.user_id,
        workspace_id=workspace_id,
        resource_type="emergency_access",
        resource_id=str(row.id),
        detail={"reason": reason_n, "requested_duration_hours": hours},
    )
    return row


def approve_emergency_access(
    db: Session,
    *,
    grant_id: int,
    approver: User,
    duration_hours: float = DEFAULT_DURATION_HOURS,
) -> EmergencyAccessGrant:
    role = normalize_role(approver.role, user_id=approver.user_id)
    if role != "super_admin":
        raise ValueError("Only super_admin may approve emergency access")

    row = db.get(EmergencyAccessGrant, grant_id)
    if not row or row.status != "pending":
        raise ValueError("Pending grant not found")
    if row.grantee_user_id == approver.user_id:
        raise ValueError("Approver cannot be the same as requester")

    hours = max(0.25, min(float(duration_hours or DEFAULT_DURATION_HOURS), MAX_DURATION_HOURS))
    now = datetime.utcnow()
    row.status = "active"
    row.approved_by_user_id = approver.user_id
    row.starts_at = now
    row.ends_at = now + timedelta(hours=hours)
    db.commit()
    db.refresh(row)
    audit_log(
        db,
        action="emergency_access.approved",
        actor_user_id=approver.user_id,
        workspace_id=row.workspace_id,
        resource_type="emergency_access",
        resource_id=str(row.id),
        detail={
            "grantee_user_id": row.grantee_user_id,
            "ends_at": row.ends_at.isoformat() + "Z",
            "reason": row.reason,
        },
    )
    return row


def deny_emergency_access(db: Session, *, grant_id: int, actor: User) -> EmergencyAccessGrant:
    if normalize_role(actor.role, user_id=actor.user_id) != "super_admin":
        raise ValueError("Only super_admin may deny emergency access")
    row = db.get(EmergencyAccessGrant, grant_id)
    if not row or row.status != "pending":
        raise ValueError("Pending grant not found")
    row.status = "denied"
    row.approved_by_user_id = actor.user_id
    db.commit()
    db.refresh(row)
    audit_log(
        db,
        action="emergency_access.denied",
        actor_user_id=actor.user_id,
        workspace_id=row.workspace_id,
        resource_type="emergency_access",
        resource_id=str(row.id),
        detail={"grantee_user_id": row.grantee_user_id},
    )
    return row


def revoke_emergency_access(db: Session, *, grant_id: int, actor: User) -> EmergencyAccessGrant:
    row = db.get(EmergencyAccessGrant, grant_id)
    if not row or row.status != "active":
        raise ValueError("Active grant not found")
    role = normalize_role(actor.role, user_id=actor.user_id)
    if role != "super_admin" and actor.user_id not in (row.grantee_user_id, row.approved_by_user_id):
        raise ValueError("Not allowed to revoke this grant")
    row.status = "revoked"
    row.revoked_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    audit_log(
        db,
        action="emergency_access.revoked",
        actor_user_id=actor.user_id,
        workspace_id=row.workspace_id,
        resource_type="emergency_access",
        resource_id=str(row.id),
        detail={},
    )
    return row


def expire_stale_grants(db: Session) -> int:
    now = datetime.utcnow()
    try:
        rows = (
            db.query(EmergencyAccessGrant)
            .filter(
                EmergencyAccessGrant.status == "active",
                EmergencyAccessGrant.ends_at.isnot(None),
                EmergencyAccessGrant.ends_at < now,
            )
            .all()
        )
    except Exception:
        db.rollback()
        return 0
    for row in rows:
        row.status = "expired"
        audit_log(
            db,
            action="emergency_access.expired",
            actor_user_id=None,
            workspace_id=row.workspace_id,
            resource_type="emergency_access",
            resource_id=str(row.id),
            detail={"auto": True},
        )
    if rows:
        db.commit()
    return len(rows)


def list_grants(
    db: Session,
    *,
    workspace_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[EmergencyAccessGrant]:
    expire_stale_grants(db)
    q = db.query(EmergencyAccessGrant).order_by(EmergencyAccessGrant.create_time.desc())
    if workspace_id is not None:
        q = q.filter(EmergencyAccessGrant.workspace_id == workspace_id)
    if status:
        q = q.filter(EmergencyAccessGrant.status == status)
    return q.limit(limit).all()


def grant_dict(row: EmergencyAccessGrant) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "grantee_user_id": row.grantee_user_id,
        "approved_by_user_id": row.approved_by_user_id,
        "reason": row.reason,
        "status": row.status,
        "starts_at": row.starts_at.isoformat() + "Z" if row.starts_at else None,
        "ends_at": row.ends_at.isoformat() + "Z" if row.ends_at else None,
        "revoked_at": row.revoked_at.isoformat() + "Z" if row.revoked_at else None,
        "create_time": row.create_time.isoformat() + "Z" if row.create_time else None,
        "read_only": True,
    }
