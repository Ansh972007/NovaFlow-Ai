"""Invite-by-email + username membership for workspaces."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import User, Workspace, WorkspaceInvite, WorkspaceMember
from app.platform.roles import WORKSPACE_ROLES, normalize_workspace_role
from app.security.audit import audit_log
from app.services.tenancy import get_membership


INVITE_TTL_DAYS = 7


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_invite(
    db: Session,
    *,
    workspace: Workspace,
    email: str,
    role: str,
    invited_by: User,
) -> tuple[WorkspaceInvite, str]:
    email_n = email.strip().lower()
    if not email_n or "@" not in email_n:
        raise ValueError("Valid email required")
    role_n = normalize_workspace_role(role)
    if role_n not in WORKSPACE_ROLES:
        raise ValueError("Invalid role")

    # If user already exists and is a member, reject
    existing_user = db.query(User).filter(User.email == email_n, User.delete == 0).first()
    if existing_user and get_membership(db, existing_user.user_id, workspace.id):
        raise ValueError("User is already a member")

    # Revoke prior pending invites for same email
    db.query(WorkspaceInvite).filter(
        WorkspaceInvite.workspace_id == workspace.id,
        WorkspaceInvite.email == email_n,
        WorkspaceInvite.status == "pending",
    ).update({"status": "revoked"})

    raw = secrets.token_urlsafe(32)
    row = WorkspaceInvite(
        workspace_id=workspace.id,
        email=email_n,
        role=role_n,
        token_hash=_hash_token(raw),
        status="pending",
        invited_by=invited_by.user_id,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit_log(
        db,
        action="workspace.invite.created",
        actor_user_id=invited_by.user_id,
        workspace_id=workspace.id,
        detail={"email": email_n, "role": role_n, "invite_id": row.id},
    )
    return row, raw


def list_invites(db: Session, workspace_id: int) -> list[WorkspaceInvite]:
    _expire_stale(db, workspace_id)
    return (
        db.query(WorkspaceInvite)
        .filter(WorkspaceInvite.workspace_id == workspace_id)
        .order_by(WorkspaceInvite.create_time.desc())
        .all()
    )


def _expire_stale(db: Session, workspace_id: int) -> None:
    now = datetime.utcnow()
    db.query(WorkspaceInvite).filter(
        WorkspaceInvite.workspace_id == workspace_id,
        WorkspaceInvite.status == "pending",
        WorkspaceInvite.expires_at < now,
    ).update({"status": "expired"})
    db.commit()


def accept_invite(db: Session, *, token: str, user: User) -> WorkspaceMember:
    th = _hash_token(token)
    row = db.query(WorkspaceInvite).filter(WorkspaceInvite.token_hash == th).first()
    if not row:
        raise ValueError("Invite not found")
    if row.status != "pending":
        raise ValueError(f"Invite is {row.status}")
    if row.expires_at < datetime.utcnow():
        row.status = "expired"
        db.commit()
        raise ValueError("Invite expired")

    # Email match when user has email set
    if user.email and user.email.strip().lower() != row.email:
        raise ValueError("Invite email does not match this account")

    existing = get_membership(db, user.user_id, row.workspace_id)
    if existing:
        row.status = "accepted"
        row.accepted_at = datetime.utcnow()
        row.accepted_user_id = user.user_id
        db.commit()
        return existing

    member = WorkspaceMember(
        workspace_id=row.workspace_id,
        user_id=user.user_id,
        role=row.role,
    )
    db.add(member)
    row.status = "accepted"
    row.accepted_at = datetime.utcnow()
    row.accepted_user_id = user.user_id
    if not user.email:
        user.email = row.email
    db.commit()
    db.refresh(member)
    audit_log(
        db,
        action="workspace.invite.accepted",
        actor_user_id=user.user_id,
        workspace_id=row.workspace_id,
        detail={"invite_id": row.id},
    )
    return member


def revoke_invite(db: Session, *, invite_id: int, workspace_id: int, actor: User) -> None:
    row = db.get(WorkspaceInvite, invite_id)
    if not row or row.workspace_id != workspace_id:
        raise ValueError("Invite not found")
    row.status = "revoked"
    db.commit()
    audit_log(
        db,
        action="workspace.invite.revoked",
        actor_user_id=actor.user_id,
        workspace_id=workspace_id,
        detail={"invite_id": invite_id},
    )
