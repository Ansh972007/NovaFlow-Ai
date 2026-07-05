import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import (
    Assistant,
    KnowledgeBase,
    UsageEvent,
    User,
    Workflow,
    WorkflowRun,
    Workspace,
    WorkspaceMember,
)


def _slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return (s[:48] or "workspace").strip("-")


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    n = 1
    while db.query(Workspace).filter(Workspace.slug == slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def ensure_personal_workspace(db: Session, user: User) -> Workspace:
    existing = (
        db.query(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == user.user_id)
        .order_by(Workspace.id)
        .first()
    )
    if existing:
        return existing

    name = f"{user.user_name}'s workspace"
    ws = Workspace(
        name=name[:120],
        slug=_unique_slug(db, _slugify(user.user_name)),
        owner_id=user.user_id,
    )
    db.add(ws)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=user.user_id,
            role="admin",
        )
    )
    db.commit()
    db.refresh(ws)
    return ws


def migrate_legacy_workspaces(db: Session) -> None:
    """Create personal workspaces and attach existing resources."""
    users = db.query(User).filter(User.delete == 0).all()
    for user in users:
        ws = ensure_personal_workspace(db, user)
        wid = ws.id
        for model in (Assistant, KnowledgeBase, Workflow):
            db.query(model).filter(
                model.user_id == user.user_id,
                (model.workspace_id.is_(None)) | (model.workspace_id == 0),
            ).update({model.workspace_id: wid}, synchronize_session=False)
        db.query(WorkflowRun).filter(
            WorkflowRun.user_id == user.user_id,
            (WorkflowRun.workspace_id.is_(None)) | (WorkflowRun.workspace_id == 0),
        ).update({WorkflowRun.workspace_id: wid}, synchronize_session=False)
        db.query(UsageEvent).filter(
            UsageEvent.user_id == user.user_id,
            (UsageEvent.workspace_id.is_(None)) | (UsageEvent.workspace_id == 0),
        ).update({UsageEvent.workspace_id: wid}, synchronize_session=False)
    db.commit()


def get_membership(db: Session, user_id: int, workspace_id: int) -> WorkspaceMember | None:
    return (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        .first()
    )


def workspace_dict(ws: Workspace, role: str | None = None) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "owner_id": ws.owner_id,
        "role": role,
        "create_time": ws.create_time.isoformat() if ws.create_time else None,
    }


def create_workspace(db: Session, user: User, name: str) -> Workspace:
    slug = _unique_slug(db, _slugify(name))
    ws = Workspace(name=name.strip()[:120], slug=slug, owner_id=user.user_id)
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.user_id, role="admin"))
    db.commit()
    db.refresh(ws)
    return ws


def add_member_by_username(
    db: Session, workspace: Workspace, username: str, role: str = "editor"
) -> WorkspaceMember | None:
    member_user = db.query(User).filter(User.user_name == username, User.delete == 0).first()
    if not member_user:
        return None
    if get_membership(db, member_user.user_id, workspace.id):
        return None
    row = WorkspaceMember(workspace_id=workspace.id, user_id=member_user.user_id, role=role)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@dataclass
class WorkspaceCtx:
    user: User
    workspace_id: int
    role: str
    workspace: Workspace
