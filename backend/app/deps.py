from typing import Callable, Optional, Union

import hashlib

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import ApiKey, User, get_db
from app.security.audit import audit_log
from app.security.rbac import ROLE_RANK, Permission, has_min_role, normalize_role
from app.security.tokens import session_is_active
from app.services.tenancy import WorkspaceCtx

# PlatformContext is the Phase-2 kernel type; WorkspaceCtx kept for typing aliases.
PlatformCtx = Union["PlatformContext", WorkspaceCtx]


def effective_role(user: User) -> str:
    return normalize_role(user.role, user_id=user.user_id)


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
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

    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    sid = payload.get("sid")
    if sid and not session_is_active(db, sid):
        audit_log(
            db,
            action="auth.session_rejected",
            actor_user_id=int(payload.get("sub") or 0) or None,
            success=False,
            detail={"reason": "session_revoked"},
            ip=request.client.host if request.client else "",
        )
        raise HTTPException(status_code=401, detail="Session revoked or expired")

    user = db.get(User, int(payload["sub"]))
    if not user or user.delete:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    token = _extract_bearer(authorization)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    sid = payload.get("sid")
    if sid and not session_is_active(db, sid):
        return None
    return db.get(User, int(payload["sub"]))


def get_platform_ctx(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[int] = Header(None, alias="X-Workspace-Id"),
    workspace_id_q: Optional[int] = Query(None, alias="workspace_id"),
    x_team_id: Optional[int] = Header(None, alias="X-Team-Id"),
):
    """Resolve PlatformContext (tenant + permission + audit + ownership)."""
    from app.platform.access import build_platform_context
    from app.platform.emergency import expire_stale_grants

    expire_stale_grants(db)
    wid = x_workspace_id or workspace_id_q
    return build_platform_context(
        db, user, workspace_id=wid, team_id=x_team_id, request=request
    )


def get_workspace_ctx(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[int] = Header(None, alias="X-Workspace-Id"),
    workspace_id_q: Optional[int] = Query(None, alias="workspace_id"),
    x_team_id: Optional[int] = Header(None, alias="X-Team-Id"),
):
    """Backward-compatible alias — returns PlatformContext (superset of WorkspaceCtx)."""
    return get_platform_ctx(
        request=request,
        db=db,
        user=user,
        x_workspace_id=x_workspace_id,
        workspace_id_q=workspace_id_q,
        x_team_id=x_team_id,
    )


def require_min_role(min_role: str) -> Callable:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if not has_min_role(effective_role(user), min_role, user_id=user.user_id):
            raise HTTPException(
                status_code=403,
                detail=f"{min_role.capitalize()} access required",
            )
        return user

    return _dep


def require_workspace_editor(ctx=Depends(get_platform_ctx)):
    ctx.require_min_role("editor")
    return ctx


def require_workspace_admin(ctx=Depends(get_platform_ctx)):
    ctx.require_min_role("admin")
    return ctx


def require_permission(permission: Permission | str) -> Callable:
    def _dep(ctx=Depends(get_platform_ctx)):
        ctx.require(permission)
        return ctx

    return _dep


require_editor = require_min_role("editor")
require_admin = require_min_role("admin")
