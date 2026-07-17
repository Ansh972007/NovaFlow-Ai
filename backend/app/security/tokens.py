"""Access + refresh token issuance, rotation, revocation, and fingerprinting."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import JWT_SECRET
from app.security.config import (
    ACCESS_TOKEN_MINUTES,
    JWT_ALGORITHM,
    JWT_ISSUER,
    MAX_SESSIONS_PER_USER,
    REFRESH_TOKEN_DAYS,
    require_secure_jwt_secret,
)


class TokenError(Exception):
    pass


def _now() -> datetime:
    return datetime.utcnow()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fingerprint(user_agent: str = "", ip: str = "") -> str:
    material = f"{user_agent}|{ip}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:32]


def issue_access_token(
    user_id: int,
    user_name: str,
    *,
    session_id: str,
    role: str = "editor",
    fingerprint: str = "",
) -> str:
    require_secure_jwt_secret()
    expire = _now() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": str(user_id),
        "user_name": user_name,
        "role": role,
        "sid": session_id,
        "fp": fingerprint,
        "typ": "access",
        "iss": JWT_ISSUER,
        "jti": uuid.uuid4().hex,
        "exp": expire,
        "iat": _now(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require_exp": True, "require_sub": True},
        )
        if payload.get("typ") not in (None, "access"):
            # Accept legacy tokens without typ during transition.
            if payload.get("typ") and payload.get("typ") != "access":
                return None
        return payload
    except JWTError:
        return None


def issue_token_pair(
    db: Session,
    user,
    *,
    user_agent: str = "",
    ip: str = "",
    device_name: str = "",
) -> dict[str, Any]:
    """Create session + access/refresh pair. Enforces concurrent session limits."""
    from app.database import AuthSession, RefreshToken

    require_secure_jwt_secret()
    fp = _fingerprint(user_agent, ip)
    session_id = uuid.uuid4().hex
    refresh_raw = secrets.token_urlsafe(48)
    family_id = uuid.uuid4().hex
    now = _now()
    access_exp = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    refresh_exp = now + timedelta(days=REFRESH_TOKEN_DAYS)

    # Evict oldest sessions beyond limit
    existing = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user.user_id, AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.asc())
        .all()
    )
    overflow = len(existing) - MAX_SESSIONS_PER_USER + 1
    if overflow > 0:
        for old in existing[:overflow]:
            old.revoked_at = now
            old.revoke_reason = "session_limit"
            db.query(RefreshToken).filter(
                RefreshToken.session_id == old.id,
                RefreshToken.revoked_at.is_(None),
            ).update({"revoked_at": now, "revoke_reason": "session_limit"})

    session = AuthSession(
        id=session_id,
        user_id=user.user_id,
        fingerprint=fp,
        user_agent=(user_agent or "")[:512],
        ip_address=(ip or "")[:64],
        device_name=(device_name or "")[:120],
        created_at=now,
        last_seen_at=now,
        absolute_expires_at=refresh_exp,
    )
    db.add(session)
    db.add(
        RefreshToken(
            id=uuid.uuid4().hex,
            user_id=user.user_id,
            session_id=session_id,
            family_id=family_id,
            token_hash=_hash_token(refresh_raw),
            expires_at=refresh_exp,
            created_at=now,
        )
    )
    db.commit()

    role = getattr(user, "role", None) or ("admin" if user.user_id == 1 else "editor")
    access = issue_access_token(
        user.user_id,
        user.user_name,
        session_id=session_id,
        role=role,
        fingerprint=fp,
    )
    return {
        "access_token": access,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "session_id": session_id,
        "access_expires_at": access_exp.isoformat() + "Z",
        "refresh_expires_at": refresh_exp.isoformat() + "Z",
    }


def rotate_refresh_token(
    db: Session,
    refresh_raw: str,
    *,
    user_agent: str = "",
    ip: str = "",
) -> dict[str, Any]:
    """Rotate refresh token (family reuse detection). Returns new pair."""
    from app.database import AuthSession, RefreshToken, User

    if not refresh_raw:
        raise TokenError("Missing refresh token")

    token_hash = _hash_token(refresh_raw)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        raise TokenError("Invalid refresh token")

    now = _now()
    if row.revoked_at is not None:
        # Reuse of revoked token → revoke entire family (theft signal)
        db.query(RefreshToken).filter(
            RefreshToken.family_id == row.family_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now, "revoke_reason": "reuse_detected"})
        db.query(AuthSession).filter(
            AuthSession.id == row.session_id,
            AuthSession.revoked_at.is_(None),
        ).update({"revoked_at": now, "revoke_reason": "reuse_detected"})
        db.commit()
        raise TokenError("Refresh token reuse detected; session family revoked")

    if row.expires_at < now:
        row.revoked_at = now
        row.revoke_reason = "expired"
        db.commit()
        raise TokenError("Refresh token expired")

    session = db.get(AuthSession, row.session_id)
    if not session or session.revoked_at is not None:
        raise TokenError("Session revoked")
    if session.absolute_expires_at and session.absolute_expires_at < now:
        session.revoked_at = now
        session.revoke_reason = "absolute_timeout"
        row.revoked_at = now
        row.revoke_reason = "absolute_timeout"
        db.commit()
        raise TokenError("Session expired")

    user = db.get(User, row.user_id)
    if not user or user.delete:
        raise TokenError("User not found")

    # Rotate: revoke old, issue new in same family
    row.revoked_at = now
    row.revoke_reason = "rotated"
    new_raw = secrets.token_urlsafe(48)
    refresh_exp = now + timedelta(days=REFRESH_TOKEN_DAYS)
    db.add(
        RefreshToken(
            id=uuid.uuid4().hex,
            user_id=user.user_id,
            session_id=session.id,
            family_id=row.family_id,
            token_hash=_hash_token(new_raw),
            expires_at=refresh_exp,
            created_at=now,
            replaced_by=None,
        )
    )
    row.replaced_by = _hash_token(new_raw)[:32]
    session.last_seen_at = now
    fp = session.fingerprint or _fingerprint(user_agent, ip)
    db.commit()

    role = user.role or ("admin" if user.user_id == 1 else "editor")
    access = issue_access_token(
        user.user_id,
        user.user_name,
        session_id=session.id,
        role=role,
        fingerprint=fp,
    )
    return {
        "access_token": access,
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "session_id": session.id,
    }


def revoke_refresh_token(db: Session, refresh_raw: str, *, reason: str = "logout") -> None:
    from app.database import AuthSession, RefreshToken

    if not refresh_raw:
        return
    token_hash = _hash_token(refresh_raw)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        return
    now = _now()
    if row.revoked_at is None:
        row.revoked_at = now
        row.revoke_reason = reason
    session = db.get(AuthSession, row.session_id)
    if session and session.revoked_at is None:
        session.revoked_at = now
        session.revoke_reason = reason
    db.commit()


def revoke_all_user_sessions(db: Session, user_id: int, *, reason: str = "logout_all") -> int:
    from app.database import AuthSession, RefreshToken

    now = _now()
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    for s in sessions:
        s.revoked_at = now
        s.revoke_reason = reason
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": now, "revoke_reason": reason})
    db.commit()
    return len(sessions)


def session_is_active(db: Session, session_id: str) -> bool:
    from app.database import AuthSession

    if not session_id:
        return True  # legacy tokens without sid
    session = db.get(AuthSession, session_id)
    if not session:
        return False
    if session.revoked_at is not None:
        return False
    if session.absolute_expires_at and session.absolute_expires_at < _now():
        return False
    return True
