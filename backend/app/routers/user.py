from datetime import datetime, timedelta
import hashlib
import hmac
import os
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.crypto import decrypt_password_plain, get_public_key_pem
from app.database import PasswordHistory, PasswordResetCode, User, get_db
from app.deps import get_current_user
from app.schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserPasswordChange,
    fail,
    ok,
)
from app.security.audit import audit_log
from app.security.middleware import client_ip
from app.security.rate_limit import rate_limiter
from app.security.passwords import (
    PasswordPolicyError,
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)
from app.security.tokens import (
    TokenError,
    issue_token_pair,
    revoke_all_user_sessions,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.ldap_auth import authenticate_ldap, find_or_create_ldap_user, ldap_status
from app.services.tenancy import ensure_personal_workspace

router = APIRouter(tags=["User"])


class RefreshBody(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutBody(BaseModel):
    refresh_token: str = ""


RESET_CODE_TTL_MINUTES = 15
RESET_CODE_MAX_ATTEMPTS = 5


def _normalise_email(value: str) -> str:
    return value.strip().lower()


def _reset_code_hash(code: str) -> str:
    secret = os.getenv("PASSWORD_RESET_SECRET") or os.getenv("JWT_SECRET", "")
    return hmac.new(secret.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def _password_reset_email(code: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="margin:0;background:#f9fafb;font-family:Arial,sans-serif;color:#111827">
  <div style="max-width:520px;margin:40px auto;background:#fff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden">
    <div style="padding:28px 32px;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;text-align:center"><strong style="font-size:22px">NovaFlow AI</strong></div>
    <div style="padding:32px"><h1 style="font-size:21px;margin-top:0">Reset your password</h1>
      <p>Use this verification code to reset your NovaFlow AI password:</p>
      <p style="margin:28px 0;padding:16px;text-align:center;font-size:30px;font-weight:700;letter-spacing:8px;background:#f3f4f6;border-radius:10px">{code}</p>
      <p>This code expires in {RESET_CODE_TTL_MINUTES} minutes and can be used once.</p>
      <p style="color:#6b7280;font-size:13px">If you did not request a password reset, you can safely ignore this email.</p>
    </div>
  </div>
</body></html>"""


def user_read(user: User, access_token: str | None = None, **extra) -> dict:
    data = {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "email": user.email,
        "delete": user.delete,
        "role": user.role or ("admin" if user.user_id == 1 else "editor"),
        "access_token": access_token,
        "create_time": user.create_time.isoformat() if user.create_time else None,
        "update_time": user.update_time.isoformat() if user.update_time else None,
    }
    data.update(extra)
    return data


def _request_meta(request: Request) -> tuple[str, str]:
    ip = client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:512]
    return ip, ua


def _issue_session(db: Session, user: User, request: Request) -> dict:
    ip, ua = _request_meta(request)
    pair = issue_token_pair(db, user, user_agent=ua, ip=ip)
    ensure_personal_workspace(db, user)
    return user_read(
        user,
        pair["access_token"],
        refresh_token=pair["refresh_token"],
        token_type=pair["token_type"],
        expires_in=pair["expires_in"],
        session_id=pair["session_id"],
    )


@router.get("/user/public_key")
def public_key():
    return ok({"public_key": get_public_key_pem()})


@router.get("/auth/ldap/status")
def ldap_auth_status():
    return ok(ldap_status())


@router.post("/user/regist")
def register(body: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.user_name == body.user_name).first():
        return fail(500, "Username already exists")
    try:
        plain = decrypt_password_plain(body.password)
    except Exception:
        return fail(400, "Invalid password payload")
    try:
        validate_password_policy(plain)
    except PasswordPolicyError as exc:
        return fail(400, str(exc))

    user = User(
        user_name=body.user_name.strip(),
        password=hash_password(plain),
        # The sign-up UI uses the email address as the username. Persist it as
        # contact email too, so password-reset emails work for new accounts.
        email=_normalise_email(body.user_name) if "@" in body.user_name else None,
        password_changed_at=datetime.utcnow(),
        role="editor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(PasswordHistory(user_id=user.user_id, password_hash=user.password))
    db.commit()
    audit_log(
        db,
        action="auth.register",
        actor_user_id=user.user_id,
        success=True,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    return ok(_issue_session(db, user, request))


@router.post("/user/login")
def login(body: UserLogin, request: Request, db: Session = Depends(get_db)):
    ip, ua = _request_meta(request)
    plain_pwd = None
    try:
        plain_pwd = decrypt_password_plain(body.password)
    except Exception:
        plain_pwd = None

    if ldap_status().get("enabled") and plain_pwd:
        try:
            profile = authenticate_ldap(body.user_name, plain_pwd)
        except RuntimeError as exc:
            return fail(503, str(exc))
        if profile:
            user = find_or_create_ldap_user(db, body.user_name, profile)
            audit_log(db, action="auth.login.ldap", actor_user_id=user.user_id, ip=ip, user_agent=ua)
            return ok(_issue_session(db, user, request))

    user = db.query(User).filter(User.user_name == body.user_name).first()
    if not user or not plain_pwd or not verify_password(plain_pwd, user.password):
        audit_log(
            db,
            action="auth.login.failed",
            success=False,
            ip=ip,
            user_agent=ua,
            detail={"user_name": body.user_name},
        )
        return {"status_code": 403, "status_message": "Invalid username or password", "data": None}

    # Transparent upgrade from legacy MD5 → Argon2id
    if needs_rehash(user.password):
        user.password = hash_password(plain_pwd)
        user.password_changed_at = user.password_changed_at or datetime.utcnow()
        db.add(PasswordHistory(user_id=user.user_id, password_hash=user.password))
        db.commit()

    audit_log(db, action="auth.login", actor_user_id=user.user_id, ip=ip, user_agent=ua)
    return ok(_issue_session(db, user, request))


@router.post("/user/password-reset/request")
def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create and email a one-time verification code without exposing account existence."""
    email = _normalise_email(body.email)
    ip = client_ip(request) or "unknown"
    if not rate_limiter.allow("password_reset", f"{ip}:{email}", limit=3, window_seconds=15 * 60):
        return fail(429, "Too many reset requests. Please wait before trying again.")

    user = (
        db.query(User)
        .filter(or_(User.email == email, User.user_name == email))
        .first()
    )
    # Always return the same result here to avoid confirming whether an email
    # address has an account. SSO-only accounts cannot use local resets.
    if not user or user.oauth_provider:
        audit_log(
            db,
            action="auth.password_reset.request",
            success=True,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            detail={"account_found": False},
        )
        return ok(None, "If an account matches this email, a verification code has been sent.")

    db.query(PasswordResetCode).filter(
        PasswordResetCode.user_id == user.user_id,
        PasswordResetCode.used_at.is_(None),
    ).update({PasswordResetCode.used_at: datetime.utcnow()}, synchronize_session=False)
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        PasswordResetCode(
            user_id=user.user_id,
            code_hash=_reset_code_hash(code),
            expires_at=datetime.utcnow() + timedelta(minutes=RESET_CODE_TTL_MINUTES),
        )
    )
    db.commit()
    audit_log(
        db,
        action="auth.password_reset.request",
        actor_user_id=user.user_id,
        ip=ip,
        user_agent=request.headers.get("user-agent", ""),
    )
    from app.services.integrations import send_email_notification

    background_tasks.add_task(
        send_email_notification,
        email,
        "Your NovaFlow AI password reset code",
        _password_reset_email(code),
    )
    return ok(None, "If an account matches this email, a verification code has been sent.")


@router.post("/user/password-reset/confirm")
def confirm_password_reset(
    body: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    email = _normalise_email(body.email)
    code = body.code.strip()
    if not code.isdigit():
        return fail(400, "Enter the six-digit verification code")
    user = db.query(User).filter(or_(User.email == email, User.user_name == email)).first()
    if not user or user.oauth_provider:
        return fail(400, "The verification code is invalid or has expired")
    record = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.user_id == user.user_id,
            PasswordResetCode.used_at.is_(None),
        )
        .order_by(PasswordResetCode.created_at.desc())
        .first()
    )
    if not record or record.expires_at < datetime.utcnow() or record.attempts >= RESET_CODE_MAX_ATTEMPTS:
        return fail(400, "The verification code is invalid or has expired")
    if not hmac.compare_digest(record.code_hash, _reset_code_hash(code)):
        record.attempts += 1
        db.commit()
        return fail(400, "The verification code is invalid or has expired")
    try:
        plain_password = decrypt_password_plain(body.new_password)
        validate_password_policy(plain_password)
    except PasswordPolicyError as exc:
        return fail(400, str(exc))
    except Exception:
        return fail(400, "Invalid new password")

    user.password = hash_password(plain_password.strip())
    user.password_changed_at = datetime.utcnow()
    user.update_time = datetime.utcnow()
    record.used_at = datetime.utcnow()
    db.add(PasswordHistory(user_id=user.user_id, password_hash=user.password))
    db.commit()
    revoke_all_user_sessions(db, user.user_id, reason="password_reset")
    audit_log(
        db,
        action="auth.password_reset.confirm",
        actor_user_id=user.user_id,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    return ok(None, "Password reset successfully. Please sign in.")


@router.post("/user/refresh")
def refresh(body: RefreshBody, request: Request, db: Session = Depends(get_db)):
    ip, ua = _request_meta(request)
    try:
        pair = rotate_refresh_token(db, body.refresh_token, user_agent=ua, ip=ip)
    except TokenError as exc:
        audit_log(db, action="auth.refresh.failed", success=False, ip=ip, detail={"error": str(exc)})
        return fail(401, str(exc))
    audit_log(db, action="auth.refresh", ip=ip, user_agent=ua)
    return ok(pair)


@router.get("/user/info")
def user_info(user: User = Depends(get_current_user)):
    return ok(user_read(user))


@router.post("/user/logout")
def logout(
    request: Request,
    body: LogoutBody = LogoutBody(),
    db: Session = Depends(get_db),
):
    """Revoke refresh session. Accepts refresh_token body; access token optional."""
    from app.crypto import decode_token

    ip = client_ip(request)
    user = None
    try:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            payload = decode_token(auth.split(" ", 1)[1].strip())
            if payload:
                user = db.get(User, int(payload["sub"]))
    except Exception:
        user = None

    if body.refresh_token:
        revoke_refresh_token(db, body.refresh_token, reason="logout")
    elif user:
        revoke_all_user_sessions(db, user.user_id, reason="logout")
    audit_log(
        db,
        action="auth.logout",
        actor_user_id=user.user_id if user else None,
        ip=ip,
    )
    return ok(None)


@router.post("/user/logout_all")
def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = revoke_all_user_sessions(db, user.user_id, reason="logout_all")
    audit_log(
        db,
        action="auth.logout_all",
        actor_user_id=user.user_id,
        ip=client_ip(request),
        detail={"sessions": count},
    )
    return ok({"revoked_sessions": count})


@router.post("/user/password")
def change_password(
    body: UserPasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.oauth_provider:
        return fail(
            400,
            "This account uses SSO sign-in. Set a password via your identity provider or contact an admin.",
        )
    try:
        current_plain = decrypt_password_plain(body.current_password)
    except Exception:
        return fail(403, "Current password is incorrect")
    if not verify_password(current_plain, user.password):
        return fail(403, "Current password is incorrect")
    try:
        plain_new = decrypt_password_plain(body.new_password)
    except Exception:
        return fail(400, "Invalid new password")
    try:
        validate_password_policy(plain_new)
    except PasswordPolicyError as exc:
        return fail(400, str(exc))

    # Reject reuse of recent passwords
    recent = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.user_id == user.user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
        .all()
    )
    for row in recent:
        if verify_password(plain_new.strip(), row.password_hash):
            return fail(400, "Password was used recently; choose a different password")

    user.password = hash_password(plain_new.strip())
    user.password_changed_at = datetime.utcnow()
    user.update_time = datetime.utcnow()
    db.add(PasswordHistory(user_id=user.user_id, password_hash=user.password))
    db.commit()
    revoke_all_user_sessions(db, user.user_id, reason="password_change")
    audit_log(db, action="auth.password_change", actor_user_id=user.user_id, ip=client_ip(request))
    return ok(None)
