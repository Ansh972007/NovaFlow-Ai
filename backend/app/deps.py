from typing import Callable, Optional

import hashlib

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import ApiKey, User, Workspace, get_db
from app.services.tenancy import WorkspaceCtx, ensure_personal_workspace, get_membership

ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}


def effective_role(user: User) -> str:
    return user.role or ("admin" if user.user_id == 1 else "editor")


def _extract_token(
    authorization: Optional[str] = Header(None),
    t: Optional[str] = Query(None),
) -> str:
    if t:
        return t
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise HTTPException(status_code=401, detail="Not authenticated")


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    t: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
) -> User:
    if x_api_key and x_api_key.startswith("nf_"):
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        row = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        if row:
            user = db.get(User, row.user_id)
            if user and not user.delete:
                return user
        raise HTTPException(status_code=401, detail="Invalid API key")
    token = _extract_token(authorization, t)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or user.delete:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    t: Optional[str] = Query(None),
) -> Optional[User]:
    try:
        token = _extract_token(authorization, t)
    except HTTPException:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return db.get(User, int(payload["sub"]))


def get_workspace_ctx(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[int] = Header(None, alias="X-Workspace-Id"),
) -> WorkspaceCtx:
    wid = x_workspace_id
    if not wid:
        ws = ensure_personal_workspace(db, user)
        wid = ws.id
    else:
        ws = db.get(Workspace, wid)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")

    membership = get_membership(db, user.user_id, wid)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return WorkspaceCtx(
        user=user,
        workspace_id=wid,
        role=membership.role or "editor",
        workspace=ws,
    )


def require_min_role(min_role: str) -> Callable:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(effective_role(user), 0) < ROLE_RANK.get(min_role, 1):
            raise HTTPException(
                status_code=403,
                detail=f"{min_role.capitalize()} access required",
            )
        return user

    return _dep


def require_workspace_editor(ctx: WorkspaceCtx = Depends(get_workspace_ctx)) -> WorkspaceCtx:
    if ROLE_RANK.get(ctx.role, 0) < ROLE_RANK.get("editor", 1):
        raise HTTPException(status_code=403, detail="Editor access required in this workspace")
    return ctx


def require_workspace_admin(ctx: WorkspaceCtx = Depends(get_workspace_ctx)) -> WorkspaceCtx:
    if ROLE_RANK.get(ctx.role, 0) < ROLE_RANK.get("admin", 1):
        raise HTTPException(status_code=403, detail="Workspace admin access required")
    return ctx


require_editor = require_min_role("editor")
require_admin = require_min_role("admin")
