"""Team CRUD within a workspace."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.database import Team, TeamMember, User
from app.security.audit import audit_log


def _slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return (s[:64] or "team").strip("-")


def create_team(
    db: Session,
    *,
    workspace_id: int,
    name: str,
    created_by: User,
    parent_team_id: int | None = None,
    description: str = "",
) -> Team:
    slug_base = _slugify(name)
    slug = slug_base
    n = 1
    while (
        db.query(Team)
        .filter(Team.workspace_id == workspace_id, Team.slug == slug, Team.deleted_at.is_(None))
        .first()
    ):
        slug = f"{slug_base}-{n}"
        n += 1

    if parent_team_id:
        parent = db.get(Team, parent_team_id)
        if not parent or parent.workspace_id != workspace_id or parent.deleted_at is not None:
            raise ValueError("Parent team not found in this workspace")

    team = Team(
        workspace_id=workspace_id,
        parent_team_id=parent_team_id,
        name=name.strip()[:120],
        slug=slug,
        description=(description or "")[:500],
        leader_user_id=created_by.user_id,
        created_by=created_by.user_id,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=created_by.user_id, role="lead"))
    db.commit()
    db.refresh(team)
    audit_log(
        db,
        action="team.created",
        actor_user_id=created_by.user_id,
        workspace_id=workspace_id,
        detail={"team_id": team.id, "name": team.name},
    )
    return team


def list_teams(db: Session, workspace_id: int) -> list[Team]:
    return (
        db.query(Team)
        .filter(Team.workspace_id == workspace_id, Team.deleted_at.is_(None))
        .order_by(Team.id)
        .all()
    )


def team_dict(team: Team) -> dict:
    return {
        "id": team.id,
        "workspace_id": team.workspace_id,
        "parent_team_id": team.parent_team_id,
        "name": team.name,
        "slug": team.slug,
        "description": team.description or "",
        "leader_user_id": team.leader_user_id,
        "create_time": team.create_time.isoformat() if team.create_time else None,
    }
