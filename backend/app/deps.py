from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import User, get_db

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
    token: str = Depends(_extract_token),
) -> User:
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


def require_min_role(min_role: str) -> Callable:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(effective_role(user), 0) < ROLE_RANK.get(min_role, 1):
            raise HTTPException(
                status_code=403,
                detail=f"{min_role.capitalize()} access required",
            )
        return user

    return _dep


require_editor = require_min_role("editor")
require_admin = require_min_role("admin")
