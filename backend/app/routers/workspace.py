from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import User, Workspace, WorkspaceMember, get_db
from app.deps import get_current_user, get_workspace_ctx, require_workspace_admin
from app.schemas import fail, ok
from app.services.tenancy import (
    add_member_by_username,
    create_workspace,
    ensure_personal_workspace,
    get_membership,
    workspace_dict,
)

router = APIRouter(tags=["Workspace"])


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == ctx.user.user_id)
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
    ws = create_workspace(db, user, name)
    return ok(workspace_dict(ws, "admin"))


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
    username = (body.get("user_name") or body.get("username") or "").strip()
    role = (body.get("role") or "editor").strip().lower()
    if role not in {"admin", "editor", "viewer"}:
        return fail(400, "Invalid role")
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return fail(404, "Workspace not found")
    row = add_member_by_username(db, ws, username, role)
    if not row:
        return fail(404, "User not found or already a member")
    u = db.get(User, row.user_id)
    return ok({"user_id": u.user_id, "user_name": u.user_name, "role": row.role})


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
    role = (body.get("role") or "").strip().lower()
    if role not in {"admin", "editor", "viewer"}:
        return fail(400, "Invalid role")
    member = get_membership(db, member_id, workspace_id)
    if not member:
        return fail(404, "Member not found")
    if member.user_id == ctx.user.user_id and role != "admin":
        return fail(400, "Cannot demote yourself")
    member.role = role
    db.commit()
    return ok({"user_id": member.user_id, "role": member.role})


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
    q.update_time = datetime.utcnow()
    db.commit()
    return ok(quotas_with_usage(db, workspace_id))
