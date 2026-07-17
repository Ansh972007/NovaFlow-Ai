from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import User, Workspace, WorkspaceMember, get_db
from app.deps import get_current_user, get_workspace_ctx, require_workspace_admin
from app.platform.invites import accept_invite, create_invite, list_invites, revoke_invite
from app.platform.roles import WORKSPACE_ROLES, normalize_workspace_role
from app.platform.teams import create_team, list_teams, team_dict
from app.schemas import fail, ok
from app.security.audit import audit_log
from app.services.tenancy import (
    WORKSPACE_TYPES,
    add_member_by_username,
    create_workspace,
    get_membership,
    workspace_dict,
)

router = APIRouter(tags=["Workspace"])


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(
            WorkspaceMember.user_id == ctx.user.user_id,
            Workspace.deleted_at.is_(None),
        )
        .order_by(Workspace.id)
        .all()
    )
    return ok(
        {
            "current_id": ctx.workspace_id,
            "items": [workspace_dict(ws, m.role) for ws, m in rows],
        }
    )


@router.post("/workspaces")
def create_workspace_api(
    body: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "Workspace name required")
    wtype = (body.get("workspace_type") or body.get("type") or "team").strip().lower()
    if wtype not in WORKSPACE_TYPES:
        wtype = "team"
    ws = create_workspace(
        db,
        user,
        name,
        workspace_type=wtype,
        region=(body.get("region") or "global"),
        timezone=(body.get("timezone") or "UTC"),
        language=(body.get("language") or "en"),
        logo_url=(body.get("logo_url") or ""),
        create_default_team=bool(body.get("create_default_team", True)),
    )
    audit_log(
        db,
        action="workspace.created",
        actor_user_id=user.user_id,
        workspace_id=ws.id,
        detail={"type": wtype, "name": name},
    )
    return ok(workspace_dict(ws, "owner"))


@router.patch("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is not None:
        return fail(404, "Workspace not found")
    if "name" in body and str(body["name"]).strip():
        ws.name = str(body["name"]).strip()[:120]
    for field in ("region", "timezone", "language", "logo_url"):
        if field in body and body[field] is not None:
            setattr(ws, field, str(body[field])[:500 if field == "logo_url" else 64])
    ws.updated_by = ctx.user.user_id
    ws.update_time = datetime.utcnow()
    db.commit()
    return ok(workspace_dict(ws, ctx.role))


@router.get("/workspaces/{workspace_id}/members")
def list_members(workspace_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    rows = (
        db.query(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.user_id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    return ok(
        [
            {
                "user_id": u.user_id,
                "user_name": u.user_name,
                "email": u.email,
                "role": m.role or "editor",
                "create_time": m.create_time.isoformat() if m.create_time else None,
            }
            for m, u in rows
        ]
    )


@router.post("/workspaces/{workspace_id}/members")
def invite_member(
    workspace_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    role = normalize_workspace_role(body.get("role") or "editor")
    if role not in WORKSPACE_ROLES:
        return fail(400, "Invalid role")
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is not None:
        return fail(404, "Workspace not found")

    email = (body.get("email") or "").strip()
    username = (body.get("user_name") or body.get("username") or "").strip()

    if email:
        try:
            invite, raw_token = create_invite(
                db, workspace=ws, email=email, role=role, invited_by=ctx.user
            )
        except ValueError as exc:
            return fail(400, str(exc))
        return ok(
            {
                "invite_id": invite.id,
                "email": invite.email,
                "role": invite.role,
                "status": invite.status,
                "expires_at": invite.expires_at.isoformat() + "Z",
                "token": raw_token,  # shown once — email delivery can use this later
            }
        )

    if not username:
        return fail(400, "email or user_name required")
    row = add_member_by_username(db, ws, username, role)
    if not row:
        return fail(404, "User not found or already a member")
    u = db.get(User, row.user_id)
    return ok({"user_id": u.user_id, "user_name": u.user_name, "role": row.role})


@router.get("/workspaces/{workspace_id}/invites")
def get_invites(workspace_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_admin)):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    rows = list_invites(db, workspace_id)
    return ok(
        [
            {
                "id": r.id,
                "email": r.email,
                "role": r.role,
                "status": r.status,
                "expires_at": r.expires_at.isoformat() + "Z" if r.expires_at else None,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
            for r in rows
        ]
    )


@router.delete("/workspaces/{workspace_id}/invites/{invite_id}")
def delete_invite(
    workspace_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    try:
        revoke_invite(db, invite_id=invite_id, workspace_id=workspace_id, actor=ctx.user)
    except ValueError as exc:
        return fail(404, str(exc))
    return ok(None)


@router.post("/workspaces/invites/accept")
def accept_workspace_invite(
    body: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    token = (body.get("token") or "").strip()
    if not token:
        return fail(400, "token required")
    try:
        member = accept_invite(db, token=token, user=user)
    except ValueError as exc:
        return fail(400, str(exc))
    return ok({"workspace_id": member.workspace_id, "role": member.role})


@router.patch("/workspaces/{workspace_id}/members/{member_id}/role")
def update_member_role_ws(
    workspace_id: int,
    member_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    role = normalize_workspace_role(body.get("role") or "")
    if role not in WORKSPACE_ROLES:
        return fail(400, "Invalid role")
    member = get_membership(db, member_id, workspace_id)
    if not member:
        return fail(404, "Member not found")
    if member.user_id == ctx.user.user_id and role not in {"owner", "admin"}:
        return fail(400, "Cannot demote yourself")
    member.role = role
    db.commit()
    return ok({"user_id": member.user_id, "role": member.role})


@router.get("/workspaces/{workspace_id}/teams")
def get_teams(workspace_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    return ok([team_dict(t) for t in list_teams(db, workspace_id)])


@router.post("/workspaces/{workspace_id}/teams")
def post_team(
    workspace_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "Team name required")
    try:
        team = create_team(
            db,
            workspace_id=workspace_id,
            name=name,
            created_by=ctx.user,
            parent_team_id=body.get("parent_team_id"),
            description=body.get("description") or "",
        )
    except ValueError as exc:
        return fail(400, str(exc))
    return ok(team_dict(team))


@router.get("/workspaces/{workspace_id}/quotas")
def get_workspace_quotas(workspace_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    from app.services.ab_routing import quotas_with_usage

    return ok(quotas_with_usage(db, workspace_id))


@router.patch("/workspaces/{workspace_id}/quotas")
def update_workspace_quotas(
    workspace_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    if ctx.workspace_id != workspace_id:
        return fail(403, "Switch to this workspace first")
    from app.database import WorkspaceQuota
    from app.services.ab_routing import quotas_with_usage

    q = db.get(WorkspaceQuota, workspace_id)
    if not q:
        q = WorkspaceQuota(workspace_id=workspace_id)
        db.add(q)
    if "eval_runs_monthly_limit" in body:
        q.eval_runs_monthly_limit = max(0, int(body["eval_runs_monthly_limit"]))
    if "finetune_jobs_monthly_limit" in body:
        q.finetune_jobs_monthly_limit = max(0, int(body["finetune_jobs_monthly_limit"]))
    if "seat_limit" in body:
        q.seat_limit = max(0, int(body["seat_limit"]))
    q.update_time = datetime.utcnow()
    db.commit()
    return ok(quotas_with_usage(db, workspace_id))
