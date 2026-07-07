import asyncio
import smtplib
from email.mime.text import MIMEText
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
    from_addr = smtp.get("from_addr") or user or "novaflow@localhost"
    msg = MIMEText(body[:8000], "plain", "utf-8")
    msg["Subject"] = subject[:200]
    msg["From"] = from_addr
    msg["To"] = to_addr
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
) -> dict:
    smtp = smtp_override or (resolve_smtp_config(db, workspace_id) if db else {})
    return await asyncio.to_thread(_send_email_sync, smtp, to_addr, subject, body)


async def send_telegram_message(
    chat_id: str,
    text: str,
    bot_token: str | None = None,
    *,
    db: Session | None = None,
    workspace_id: int | None = None,
) -> dict:
    token = resolve_telegram_token(db, workspace_id, bot_token or "") if db else (bot_token or TELEGRAM_BOT_TOKEN or "").strip()
    if not token or not chat_id:
        return {"ok": False, "detail": "Telegram bot token or chat_id missing — add in Settings → Integrations"}
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


async def send_notification(
    channel: str,
    to_addr: str,
    subject: str,
    body: str,
    *,
    bot_token: str = "",
    db: Session | None = None,
    workspace_id: int | None = None,
) -> dict:
    ch = (channel or "telegram").strip().lower()
    if ch == "email":
        return await send_email_notification(to_addr, subject, body, db=db, workspace_id=workspace_id)
    if ch == "webhook":
        return await send_webhook_notification(to_addr, subject, body)
    return await send_telegram_message(
        to_addr,
        body,
        bot_token or None,
        db=db,
        workspace_id=workspace_id,
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
