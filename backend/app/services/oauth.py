import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.config import (
    FRONTEND_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    JWT_SECRET,
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET,
    OAUTH_REDIRECT_BASE,
)
from app.crypto import create_token, md5_hash
from app.database import User
from sqlalchemy.orm import Session


def _provider_config() -> dict[str, dict[str, Any]]:
    return {
        "google": {
            "label": "Google",
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        },
        "microsoft": {
            "label": "Microsoft",
            "client_id": MICROSOFT_CLIENT_ID,
            "client_secret": MICROSOFT_CLIENT_SECRET,
            "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "scope": "openid email profile User.Read",
        },
    }


def list_enabled_providers() -> list[dict[str, str]]:
    items = []
    for key, cfg in _provider_config().items():
        if cfg["client_id"] and cfg["client_secret"]:
            items.append({"id": key, "label": cfg["label"]})
    return items


def redirect_uri(provider: str) -> str:
    base = OAUTH_REDIRECT_BASE.rstrip("/")
    return f"{base}/api/v1/auth/oauth/{provider}/callback"


def create_oauth_state(provider: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=10)
    return jwt.encode(
        {"provider": provider, "nonce": secrets.token_urlsafe(12), "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def verify_oauth_state(state: str, provider: str) -> bool:
    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        return payload.get("provider") == provider
    except JWTError:
        return False


def build_authorize_url(provider: str) -> str | None:
    cfg = _provider_config().get(provider)
    if not cfg or not cfg["client_id"] or not cfg["client_secret"]:
        return None
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": create_oauth_state(provider),
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{cfg['authorize_url']}?{urlencode(params)}"


async def exchange_code(provider: str, code: str) -> dict[str, Any]:
    cfg = _provider_config()[provider]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_userinfo(provider: str, token_data: dict[str, Any]) -> dict[str, Any]:
    cfg = _provider_config()[provider]
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("No access token")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code >= 400 and provider == "microsoft":
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        resp.raise_for_status()
        data = resp.json()

    email = data.get("email") or data.get("preferred_username") or data.get("mail") or data.get("userPrincipalName")
    name = data.get("name") or data.get("displayName") or ""
    sub = str(data.get("sub") or data.get("id") or "")
    if not sub:
        raise ValueError("OAuth profile missing subject id")
    return {"email": email, "name": name, "sub": sub}


def _unique_username(db: Session, email: str | None, name: str, sub: str) -> str:
    import re

    if email:
        base = re.sub(r"[^\w.-]", "", email.split("@")[0])[:48]
    elif name:
        base = re.sub(r"[^\w.-]", "", name.replace(" ", "."))[:48]
    else:
        base = f"user_{sub[:8]}"
    if not base:
        base = f"user_{sub[:8]}"
    candidate = base
    n = 1
    while db.query(User).filter(User.user_name == candidate).first():
        candidate = f"{base[:40]}_{n}"
        n += 1
    return candidate[:64]


def find_or_create_oauth_user(
    db: Session,
    provider: str,
    sub: str,
    email: str | None,
    name: str,
) -> User:
    user = (
        db.query(User)
        .filter(User.oauth_provider == provider, User.oauth_subject == sub)
        .first()
    )
    if user:
        if email and not user.email:
            user.email = email
            db.commit()
        return user

    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.oauth_provider = provider
            existing.oauth_subject = sub
            db.commit()
            return existing

    username = _unique_username(db, email, name, sub)
    user = User(
        user_name=username,
        email=email,
        password=md5_hash(secrets.token_urlsafe(32)),
        oauth_provider=provider,
        oauth_subject=sub,
        role="editor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def frontend_callback_url(access_token: str) -> str:
    base = FRONTEND_URL.rstrip("/")
    return f"{base}/login/oauth-callback?token={access_token}"
