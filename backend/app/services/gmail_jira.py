"""Gmail OAuth (workspace mail) + Jira Cloud helpers."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import FRONTEND_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, JWT_SECRET, OAUTH_REDIRECT_BASE
from app.crypto import decrypt_secret, encrypt_secret
from app.database import WorkspaceIntegration
from app.services.workspace_integrations import get_or_create

GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email openid"


def gmail_oauth_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def gmail_redirect_uri() -> str:
    base = OAUTH_REDIRECT_BASE.rstrip("/")
    return f"{base}/api/v1/integrations/gmail/oauth/callback"


def create_gmail_oauth_state(workspace_id: int, user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode(
        {
            "purpose": "gmail_oauth",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "exp": expire,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def verify_gmail_oauth_state(state: str) -> dict | None:
    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        if payload.get("purpose") != "gmail_oauth":
            return None
        return payload
    except JWTError:
        return None


def build_gmail_authorize_url(workspace_id: int, user_id: int) -> str | None:
    if not gmail_oauth_enabled():
        return None
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": gmail_redirect_uri(),
        "response_type": "code",
        "scope": GMAIL_SCOPES,
        "state": create_gmail_oauth_state(workspace_id, user_id),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_gmail_code(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": gmail_redirect_uri(),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_gmail_access_token(refresh_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_gmail_profile(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def store_gmail_oauth_tokens(
    db: Session,
    workspace_id: int,
    token_data: dict[str, Any],
    email: str,
) -> WorkspaceIntegration:
    row = get_or_create(db, workspace_id)
    refresh = (token_data.get("refresh_token") or "").strip()
    access = (token_data.get("access_token") or "").strip()
    if refresh:
        row.gmail_oauth_refresh_token_enc = encrypt_secret(refresh)
    if access:
        row.gmail_oauth_access_token_enc = encrypt_secret(access)
    expires_in = int(token_data.get("expires_in") or 3600)
    row.gmail_oauth_token_expiry = datetime.utcnow() + timedelta(seconds=max(60, expires_in - 60))
    row.gmail_oauth_email = (email or "").strip()[:255]
    row.gmail_oauth_connected_at = datetime.utcnow()
    row.gmail_auth_mode = "oauth"
    if email and not row.smtp_from:
        row.smtp_from = email[:255]
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def disconnect_gmail_oauth(db: Session, workspace_id: int) -> None:
    row = get_or_create(db, workspace_id)
    row.gmail_oauth_refresh_token_enc = ""
    row.gmail_oauth_access_token_enc = ""
    row.gmail_oauth_token_expiry = None
    row.gmail_oauth_email = ""
    row.gmail_oauth_connected_at = None
    row.gmail_auth_mode = "smtp"
    row.updated_at = datetime.utcnow()
    db.commit()


async def get_valid_gmail_access_token(db: Session, workspace_id: int) -> str:
    row = db.get(WorkspaceIntegration, workspace_id)
    if not row or not row.gmail_oauth_refresh_token_enc:
        raise ValueError("Gmail OAuth not connected")
    refresh = decrypt_secret(row.gmail_oauth_refresh_token_enc)
    if not refresh:
        raise ValueError("Gmail refresh token missing")

    access = decrypt_secret(row.gmail_oauth_access_token_enc or "")
    expiry = row.gmail_oauth_token_expiry
    if access and expiry and expiry > datetime.utcnow() + timedelta(minutes=2):
        return access

    token_data = await refresh_gmail_access_token(refresh)
    access = (token_data.get("access_token") or "").strip()
    if not access:
        raise ValueError("Failed to refresh Gmail access token")
    row.gmail_oauth_access_token_enc = encrypt_secret(access)
    expires_in = int(token_data.get("expires_in") or 3600)
    row.gmail_oauth_token_expiry = datetime.utcnow() + timedelta(seconds=max(60, expires_in - 60))
    if token_data.get("refresh_token"):
        row.gmail_oauth_refresh_token_enc = encrypt_secret(token_data["refresh_token"])
    row.updated_at = datetime.utcnow()
    db.commit()
    return access


async def send_gmail_api_message(
    db: Session,
    workspace_id: int,
    to_addr: str,
    subject: str,
    body: str,
) -> dict:
    if not to_addr:
        return {"ok": False, "detail": "Missing recipient"}
    try:
        access = await get_valid_gmail_access_token(db, workspace_id)
        row = db.get(WorkspaceIntegration, workspace_id)
        from_addr = (row.gmail_oauth_email if row else "") or "me"
        msg = MIMEText(body[:8000], "plain", "utf-8")
        msg["To"] = to_addr
        msg["Subject"] = subject[:200]
        msg["From"] = from_addr
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access}"},
                json={"raw": raw},
            )
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
        return {"ok": True, "detail": f"Gmail sent to {to_addr}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


def resolve_jira_config(db: Session, workspace_id: int | None) -> dict[str, Any]:
    if not workspace_id:
        return {"base_url": "", "email": "", "api_token": "", "configured": False}
    row = db.get(WorkspaceIntegration, workspace_id)
    if not row:
        return {"base_url": "", "email": "", "api_token": "", "configured": False}
    token = decrypt_secret(row.jira_api_token_enc or "") if row.jira_api_token_enc else ""
    base = (row.jira_base_url or "").strip().rstrip("/")
    email = (row.jira_email or "").strip()
    return {
        "base_url": base,
        "email": email,
        "api_token": token,
        "configured": bool(base and email and token),
    }


def _jira_auth_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _plain_to_adf(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": (text or "")[:5000] or " "}],
            }
        ],
    }


async def jira_verify(db: Session, workspace_id: int) -> dict:
    cfg = resolve_jira_config(db, workspace_id)
    if not cfg["configured"]:
        return {"ok": False, "detail": "Jira not configured — add base URL, email, and API token"}
    url = f"{cfg['base_url']}/rest/api/3/myself"
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": _jira_auth_header(cfg["email"], cfg["api_token"]),
                    "Accept": "application/json",
                },
            )
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
            data = resp.json()
            return {
                "ok": True,
                "detail": f"Connected as {data.get('displayName') or data.get('emailAddress') or cfg['email']}",
                "account": data,
            }
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def jira_create_issue(
    db: Session,
    workspace_id: int,
    *,
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Task",
) -> dict:
    cfg = resolve_jira_config(db, workspace_id)
    if not cfg["configured"]:
        raise ValueError("Jira not configured in Settings → Integrations")
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": (summary or "NovaFlow issue")[:255],
            "issuetype": {"name": issue_type or "Task"},
            "description": _plain_to_adf(description or summary),
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{cfg['base_url']}/rest/api/3/issue",
            headers={
                "Authorization": _jira_auth_header(cfg["email"], cfg["api_token"]),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        return resp.json()


async def jira_update_issue(
    db: Session,
    workspace_id: int,
    *,
    issue_key: str,
    summary: str = "",
    description: str = "",
) -> dict:
    cfg = resolve_jira_config(db, workspace_id)
    if not cfg["configured"]:
        raise ValueError("Jira not configured in Settings → Integrations")
    fields: dict[str, Any] = {}
    if summary:
        fields["summary"] = summary[:255]
    if description:
        fields["description"] = _plain_to_adf(description)
    if not fields:
        raise ValueError("Nothing to update")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(
            f"{cfg['base_url']}/rest/api/3/issue/{issue_key}",
            headers={
                "Authorization": _jira_auth_header(cfg["email"], cfg["api_token"]),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"fields": fields},
        )
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        return {"key": issue_key, "updated": True}


def frontend_settings_redirect(query: str = "") -> str:
    base = FRONTEND_URL.rstrip("/")
    q = f"?{query}" if query else ""
    return f"{base}/settings{q}"
