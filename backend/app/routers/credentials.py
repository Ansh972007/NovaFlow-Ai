"""Credentials vault API — multi-slot secrets per workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import WorkspaceIntegration, get_db
from app.deps import require_permission
from app.schemas import fail, ok
from app.security.rbac import Permission
from app.services import credential_vault as vault

router = APIRouter(prefix="/credentials", tags=["Credentials"])


def _humanize_verify_detail(exc: Exception) -> str:
    s = str(exc).strip()
    low = s.lower()
    if "username and password not accepted" in low or "badcredentials" in low or "535" in s:
        return "Gmail rejected the login. Use an App Password or connect with Google OAuth."
    if "invalid_grant" in low or "token refresh failed" in low:
        return "Google OAuth expired. Reconnect with Google."
    if "401" in s or "invalid api key" in low:
        return "API key was rejected. Check the key and try again."
    if "unauthorized" in low or "bot token" in low or "not found" in low and "bot" in low:
        return "Bot token rejected. Copy the full token from @BotFather."
    if "smtp user and password required" in low:
        return "Enter your email address and App Password."
    if s.startswith("(535,") or "gsmtp" in low:
        return "Email login failed. For Gmail, use an App Password or OAuth."
    if len(s) > 200:
        return s[:200] + "…"
    return s or "Verification failed"


@router.get("/catalog")
def catalog(ctx=Depends(require_permission(Permission.INTEGRATION_READ))):
    return ok(vault.get_catalog())


@router.get("/oauth-setup")
def oauth_setup(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    return ok(vault.get_oauth_setup_info(db, ctx.workspace_id))


@router.get("/overview")
def credentials_overview(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    return ok(vault.overview(db, ctx.workspace_id))


@router.get("")
@router.get("/")
def list_credentials(
    category: str | None = None,
    kind: str | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    rows = vault.list_entries(db, ctx.workspace_id, category=category, kind=kind)
    return ok([vault.serialize_entry(r) for r in rows])


@router.post("")
@router.post("/")
def create_credential(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    category = (body.get("category") or "").strip()
    kind = (body.get("kind") or "").strip()
    label = (body.get("label") or "default").strip()
    fields = body.get("fields") if isinstance(body.get("fields"), dict) else {}
    is_default = bool(body.get("is_default"))
    if not category or not kind:
        return fail(400, "category and kind are required")
    try:
        row = vault.create_entry(
            db,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.user_id,
            category=category,
            kind=kind,
            label=label,
            fields=fields,
            is_default=is_default,
        )
    except ValueError as exc:
        return fail(400, str(exc))
    if row.category == "telegram" and row.kind == "telegram_bot":
        vault.auto_verify_telegram(db, row)
        row = vault.get_entry(db, ctx.workspace_id, row.id)
    ctx.audit("credential.created", resource_type="credential", resource_id=row.id)
    return ok(vault.serialize_entry(row))


@router.get("/{entry_id}")
def get_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    return ok(vault.serialize_entry(row))


@router.patch("/{entry_id}")
def patch_credential(
    entry_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    fields = body.get("fields") if isinstance(body.get("fields"), dict) else None
    label = body.get("label")
    is_default = body.get("is_default")
    if is_default is not None:
        is_default = bool(is_default)
    row = vault.update_entry(
        db,
        row,
        fields=fields,
        label=label if label is not None else None,
        is_default=is_default,
    )
    if (
        row.category == "telegram"
        and row.kind == "telegram_bot"
        and isinstance(body.get("fields"), dict)
        and (body["fields"].get("bot_token") or "").strip()
    ):
        vault.auto_verify_telegram(db, row)
        row = vault.get_entry(db, ctx.workspace_id, row.id)
    ctx.audit("credential.updated", resource_type="credential", resource_id=row.id)
    return ok(vault.serialize_entry(row))


@router.delete("/{entry_id}")
def delete_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    vault.delete_entry(db, row)
    ctx.audit("credential.deleted", resource_type="credential", resource_id=entry_id)
    return ok(None)


@router.post("/{entry_id}/set-default")
def set_default_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    row = vault.set_default(db, row)
    return ok(vault.serialize_entry(row))


@router.post("/{entry_id}/verify")
async def verify_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    fields = vault.resolve_fields(
        db, ctx.workspace_id, category=row.category, kind=row.kind, credential_id=row.id
    )
    detail = "ok"
    status = "ok"
    try:
        if row.category == "telegram" and fields.get("bot_token"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"https://api.telegram.org/bot{fields['bot_token']}/getMe")
                data = r.json()
                if not data.get("ok"):
                    raise ValueError(data.get("description") or "Telegram verify failed")
                detail = f"@{data.get('result', {}).get('username') or 'bot'}"
                if data.get("result", {}).get("username"):
                    vault.update_entry(
                        db,
                        row,
                        fields={"bot_username": data["result"]["username"]},
                    )
        elif row.category == "llm" and fields.get("api_key"):
            import httpx

            base = (fields.get("base_url") or "https://api.openai.com/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {fields['api_key']}"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"LLM verify failed ({r.status_code})")
                detail = "models reachable"
        elif row.category == "slack" and fields.get("webhook_url"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    fields["webhook_url"],
                    json={"text": "NovaFlow credentials verify ✅"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"Slack webhook failed ({r.status_code})")
                detail = "webhook accepted"
        elif row.category == "discord" and fields.get("webhook_url"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    fields["webhook_url"],
                    json={"content": "NovaFlow credentials verify ✅"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"Discord webhook failed ({r.status_code})")
                detail = "webhook accepted"
        elif row.category == "email" and row.kind == "gmail_smtp":
            import asyncio
            import smtplib

            def _smtp_login() -> str:
                host = (fields.get("smtp_host") or "smtp.gmail.com").strip()
                port = int(fields.get("smtp_port") or 587)
                user = (fields.get("smtp_user") or "").strip()
                password = (fields.get("smtp_password") or "").strip()
                if not user or not password:
                    raise ValueError("SMTP user and password required")
                with smtplib.SMTP(host, port, timeout=20) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(user, password)
                return f"SMTP login ok ({user})"

            detail = await asyncio.to_thread(_smtp_login)
        elif row.category == "email" and row.kind == "gmail_oauth":
            from app.services.gmail_jira import resolve_google_oauth_client

            refresh = (fields.get("refresh_token") or "").strip()
            access = (fields.get("access_token") or "").strip()
            client_id = (fields.get("client_id") or "").strip()
            client_secret = (fields.get("client_secret") or "").strip()
            if not client_id or not client_secret:
                client_id, client_secret = resolve_google_oauth_client(db, ctx.workspace_id)
            if not refresh and not access:
                row_ws = db.get(WorkspaceIntegration, ctx.workspace_id)
                if row_ws and row_ws.gmail_oauth_refresh_token_enc:
                    detail = f"Gmail OAuth connected ({row_ws.gmail_oauth_email or 'account'})"
                elif client_id and client_secret:
                    detail = "Client ID and secret saved — use Connect with Google to finish"
                else:
                    raise ValueError("Enter Client ID and Client secret, then Save")
            else:
                if not client_id or not client_secret:
                    raise ValueError("Client ID and Client secret are required")
                if refresh and client_id and client_secret:
                    import httpx

                    async with httpx.AsyncClient(timeout=20) as client:
                        r = await client.post(
                            "https://oauth2.googleapis.com/token",
                            data={
                                "client_id": client_id,
                                "client_secret": client_secret,
                                "refresh_token": refresh,
                                "grant_type": "refresh_token",
                            },
                        )
                        if r.status_code >= 400:
                            raise ValueError(f"Google token refresh failed ({r.status_code})")
                        data = r.json()
                        if not data.get("access_token"):
                            raise ValueError("Google returned no access token")
                        detail = "Gmail OAuth token valid"
                elif access:
                    import httpx

                    async with httpx.AsyncClient(timeout=15) as client:
                        r = await client.get(
                            "https://openidconnect.googleapis.com/v1/userinfo",
                            headers={"Authorization": f"Bearer {access}"},
                        )
                        if r.status_code >= 400:
                            raise ValueError("Gmail access token invalid")
                        detail = f"Gmail OAuth ok ({r.json().get('email') or 'account'})"
                else:
                    detail = "Gmail OAuth tokens stored"
        elif row.category == "google" and row.kind == "google_oauth":
            client_id = (fields.get("client_id") or "").strip()
            client_secret = (fields.get("client_secret") or "").strip()
            refresh = (fields.get("refresh_token") or "").strip()
            if not client_id or not client_secret:
                raise ValueError("Client ID and client secret are required")
            if refresh:
                import httpx

                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "refresh_token": refresh,
                            "grant_type": "refresh_token",
                        },
                    )
                    if r.status_code >= 400:
                        raise ValueError(f"Google OAuth verify failed ({r.status_code})")
                    if not r.json().get("access_token"):
                        raise ValueError("Invalid refresh token")
                    detail = "Google OAuth credentials valid"
            else:
                detail = "Client ID/secret stored — add refresh token to fully verify"
        elif row.category == "github":
            from app.services.github_issues import github_verify

            result = await github_verify(db, ctx.workspace_id, credential_id=row.id)
            if not result.get("ok"):
                raise ValueError(result.get("detail") or "GitHub verify failed")
            detail = result.get("detail") or "ok"
        elif row.category == "jira":
            from app.services.gmail_jira import jira_verify

            result = await jira_verify(db, ctx.workspace_id, credential_id=row.id)
            if not result.get("ok"):
                raise ValueError(result.get("detail") or "Jira verify failed")
            detail = result.get("detail") or "ok"
        elif row.category == "linear":
            from app.services.linear_issues import linear_verify

            result = await linear_verify(db, ctx.workspace_id, credential_id=row.id)
            if not result.get("ok"):
                raise ValueError(result.get("detail") or "Linear verify failed")
            detail = result.get("detail") or "ok"
        elif row.category == "outlook" and row.kind == "microsoft_graph":
            if fields.get("access_token") or fields.get("refresh_token"):
                detail = "OAuth tokens stored — use Microsoft Graph test from integrations"
            else:
                detail = "tenant/client fields stored — complete OAuth in Settings → Integrations"
        else:
            detail = "stored"
        vault.update_entry(db, row, status="ok")
    except Exception as exc:
        status = "error"
        detail = _humanize_verify_detail(exc)
        vault.update_entry(db, row, status="error")
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    return ok({"status": status, "detail": detail, "credential": vault.serialize_entry(row)})
