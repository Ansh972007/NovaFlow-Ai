import asyncio
import smtplib
import time
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import TELEGRAM_BOT_TOKEN
from app.services.workspace_integrations import resolve_smtp_config, resolve_telegram_token


def _send_email_sync(smtp: dict[str, Any], to_addr: str, subject: str, body: str) -> dict:
    host = smtp.get("host") or ""
    if not host or not to_addr:
        return {"ok": False, "detail": "SMTP not configured or missing recipient"}
    port = int(smtp.get("port") or 587)
    user = smtp.get("user") or ""
    password = smtp.get("password") or ""
    # Gmail app passwords are often pasted with spaces
    password = "".join(str(password).split())
    from_addr = smtp.get("from_addr") or user or "novaflow@localhost"
    
    from email.utils import formataddr, make_msgid, formatdate
    
    if "@" in from_addr and "<" not in from_addr:
        from_formatted = formataddr(("NovaFlow AI", from_addr))
    else:
        from_formatted = from_addr
        
    subtype = "html" if (body.strip().startswith("<") or "<html>" in body.lower()) else "plain"
    msg = MIMEText(body, subtype, "utf-8")
    msg["Subject"] = subject[:200]
    msg["From"] = from_formatted
    msg["To"] = to_addr
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg["Date"] = formatdate(localtime=True)
    msg["MIME-Version"] = "1.0"
    
    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return {"ok": True, "detail": f"Email sent to {to_addr}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_email_notification(
    to_addr: str,
    subject: str,
    body: str,
    *,
    db: Session | None = None,
    workspace_id: int | None = None,
    smtp_override: dict | None = None,
    credential_id: str | None = None,
) -> dict:
    if db and workspace_id and not smtp_override and not credential_id:
        from app.database import WorkspaceIntegration
        from app.services.gmail_jira import send_gmail_api_message

        row = db.get(WorkspaceIntegration, workspace_id)
        if row and (row.gmail_auth_mode or "").lower() == "oauth" and row.gmail_oauth_refresh_token_enc:
            return await send_gmail_api_message(db, workspace_id, to_addr, subject, body)

    smtp = smtp_override or (
        resolve_smtp_config(db, workspace_id, credential_id=credential_id) if db else {}
    )
    
    # Fallback to platform SMTP (password reset / invites / missing workspace mail)
    if not smtp or not smtp.get("host") or not smtp.get("password"):
        from app.services.platform_mail import platform_smtp_config

        platform = platform_smtp_config()
        if not smtp:
            smtp = platform
        else:
            smtp = {
                "host": smtp.get("host") or platform.get("host"),
                "port": smtp.get("port") or platform.get("port"),
                "user": smtp.get("user") or platform.get("user"),
                "password": smtp.get("password") or platform.get("password"),
                "from_addr": smtp.get("from_addr") or platform.get("from_addr"),
            }

    return await asyncio.to_thread(_send_email_sync, smtp, to_addr, subject, body)


async def send_telegram_message(
    chat_id: str,
    text: str,
    bot_token: str | None = None,
    *,
    db: Session | None = None,
    workspace_id: int | None = None,
    credential_id: str | None = None,
) -> dict:
    token = (
        resolve_telegram_token(db, workspace_id, bot_token or "", credential_id=credential_id)
        if db
        else (bot_token or TELEGRAM_BOT_TOKEN or "").strip()
    )
    if not token or not chat_id:
        return {"ok": False, "detail": "Telegram bot token or chat_id missing — add in Credentials"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json={"chat_id": chat_id, "text": text[:4096]},
            )
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                return {"ok": False, "detail": str(payload.get("description") or "Telegram API error")}
            return {"ok": True, "detail": f"Telegram message sent to {chat_id}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_webhook_notification(url: str, subject: str, body: str) -> dict:
    if not url:
        return {"ok": False, "detail": "Webhook URL missing"}
    from app.services.webhooks import post_webhook

    try:
        await post_webhook(url, {"subject": subject, "body": body, "source": "novaflow_notify"})
        return {"ok": True, "detail": f"Webhook posted to {url[:80]}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_slack_notification(
    text: str,
    *,
    webhook_url: str = "",
    db: Session | None = None,
    workspace_id: int | None = None,
    subject: str = "",
) -> dict:
    from app.services.workspace_integrations import resolve_slack_webhook

    url = resolve_slack_webhook(db, workspace_id, webhook_url) if db else (webhook_url or "").strip()
    if not url:
        return {"ok": False, "detail": "Slack webhook missing — add in Settings → Integrations"}
    message = text[:3900]
    if subject and subject.strip() and subject.strip().lower() not in ("novaflow", "novaflow notification"):
        message = f"*{subject.strip()[:120]}*\n{message}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json={"text": message})
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
            return {"ok": True, "detail": "Slack message posted"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_discord_notification(
    text: str,
    *,
    webhook_url: str = "",
    db: Session | None = None,
    workspace_id: int | None = None,
    subject: str = "",
) -> dict:
    from app.services.workspace_integrations import resolve_discord_webhook

    url = resolve_discord_webhook(db, workspace_id, webhook_url) if db else (webhook_url or "").strip()
    if not url:
        return {"ok": False, "detail": "Discord webhook missing — add in Settings → Integrations"}
    message = text[:1900]
    if subject and subject.strip() and subject.strip().lower() not in ("novaflow", "novaflow notification"):
        message = f"**{subject.strip()[:120]}**\n{message}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json={"content": message})
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
            return {"ok": True, "detail": "Discord message posted"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_whatsapp_notification(
    to_phone: str,
    body: str,
    *,
    db: Session | None = None,
    workspace_id: int | None = None,
    credential_id: str | None = None,
) -> dict:
    from app.services import credential_vault as vault

    fields = (
        vault.resolve_fields(
            db,
            workspace_id,
            category="whatsapp",
            kind="whatsapp_cloud",
            credential_id=credential_id,
        )
        if db and workspace_id
        else {}
    )
    token = (fields.get("access_token") or "").strip()
    phone_id = (fields.get("phone_number_id") or "").strip()
    if not token or not phone_id:
        return {
            "ok": False,
            "detail": "WhatsApp Cloud API credentials missing — add access token and phone number ID",
        }
    if not to_phone:
        return {"ok": False, "detail": "WhatsApp recipient phone missing"}
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone.replace("+", "").replace(" ", "").strip(),
        "type": "text",
        "text": {"body": body[:4096]},
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
        return {"ok": True, "detail": f"WhatsApp message sent to {to_phone}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def send_notification(
    channel: str,
    to_addr: str,
    subject: str,
    body: str,
    *,
    bot_token: str = "",
    db: Session | None = None,
    workspace_id: int | None = None,
    credential_id: str | None = None,
) -> dict:
    ch = (channel or "telegram").strip().lower()
    if ch == "email":
        return await send_email_notification(
            to_addr, subject, body, db=db, workspace_id=workspace_id, credential_id=credential_id
        )
    if ch == "webhook":
        return await send_webhook_notification(to_addr, subject, body)
    if ch == "slack":
        return await send_slack_notification(
            body,
            webhook_url=to_addr,
            db=db,
            workspace_id=workspace_id,
            subject=subject,
        )
    if ch == "discord":
        return await send_discord_notification(
            body,
            webhook_url=to_addr,
            db=db,
            workspace_id=workspace_id,
            subject=subject,
        )
    if ch == "whatsapp":
        return await send_whatsapp_notification(
            to_addr,
            body,
            db=db,
            workspace_id=workspace_id,
            credential_id=credential_id,
        )
    return await send_telegram_message(
        to_addr,
        body,
        bot_token or None,
        db=db,
        workspace_id=workspace_id,
        credential_id=credential_id,
    )


async def register_telegram_webhook(
    db: Session,
    workspace_id: int,
    webhook_url: str,
    bot_token: str = "",
) -> dict:
    token = resolve_telegram_token(db, workspace_id, bot_token)
    if not token:
        return {"ok": False, "detail": "Telegram bot token not configured"}
    if not webhook_url:
        return {"ok": False, "detail": "Webhook URL required"}
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"url": webhook_url})
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                return {"ok": False, "detail": str(payload.get("description") or "setWebhook failed")}
            return {"ok": True, "detail": "Telegram webhook registered", "result": payload.get("result")}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def get_telegram_bot_info(db: Session, workspace_id: int, bot_token: str = "") -> dict:
    token = resolve_telegram_token(db, workspace_id, bot_token)
    if not token:
        return {"ok": False, "detail": "Telegram bot token not configured"}
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                return {"ok": False, "detail": str(payload.get("description") or "getMe failed")}
            return {"ok": True, "bot": payload.get("result")}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


from app.services.workspace_integrations import resolve_telegram_token


async def get_telegram_webhook_info(db: Session, workspace_id: int, bot_token: str = "") -> dict:
    token = resolve_telegram_token(db, workspace_id, bot_token)
    if not token:
        return {"ok": False, "detail": "Telegram bot token not configured"}
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                return {"ok": False, "detail": str(payload.get("description") or "getWebhookInfo failed")}
            return {"ok": True, "info": payload.get("result") or {}}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


def parse_telegram_input(payload: dict) -> tuple[str, str]:
    """Return (chat_id, text) from a Telegram webhook update."""
    message = payload.get("message") or payload.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    return chat_id, text


def parse_slack_event(payload: dict) -> tuple[str, str, str]:
    """Return (channel_id, user_id, text) from a Slack Events API payload."""
    event = payload.get("event") or {}
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return "", "", ""
    text = (event.get("text") or "").strip()
    # Strip Slack user mentions like <@U123>
    import re

    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    return str(event.get("channel") or ""), str(event.get("user") or ""), text


def verify_slack_signature(signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        if abs(int(time.time()) - int(timestamp)) > 60 * 5:
            return False
    except ValueError:
        return False
    import hashlib
    import hmac

    basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
    digest = "v0=" + hmac.new(signing_secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


async def send_slack_bot_message(db: Session, workspace_id: int, channel: str, text: str) -> dict:
    from app.crypto import decrypt_secret
    from app.database import WorkspaceIntegration

    row = db.get(WorkspaceIntegration, workspace_id)
    token = decrypt_secret(row.slack_bot_token_enc or "") if row and row.slack_bot_token_enc else ""
    if not token or not channel:
        return {"ok": False, "detail": "Slack bot token or channel missing"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"channel": channel, "text": text[:3900]},
            )
            data = resp.json()
            if not data.get("ok"):
                return {"ok": False, "detail": str(data.get("error") or "chat.postMessage failed")}
            return {"ok": True, "detail": "Slack bot reply posted"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}
