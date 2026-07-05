from typing import Optional

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import User, get_db


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
