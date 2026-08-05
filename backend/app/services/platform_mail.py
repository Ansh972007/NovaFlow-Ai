"""Platform transactional email — password reset, team invites.

Uses server-side SMTP only. The app password must never appear in API
responses, frontend bundles, or logs.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def platform_smtp_config() -> dict[str, Any]:
    from app.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

    user = (SMTP_USER or "").strip()
    password = "".join((SMTP_PASSWORD or "").split())  # strip spaces for Gmail app passwords
    host = (SMTP_HOST or "").strip() or ("smtp.gmail.com" if user.endswith("@gmail.com") else "")
    return {
        "host": host,
        "port": int(SMTP_PORT or 587),
        "user": user,
        "password": password,
        "from_addr": (SMTP_FROM or user or "").strip(),
    }


def platform_mail_ready() -> bool:
    cfg = platform_smtp_config()
    return bool(cfg.get("host") and cfg.get("user") and cfg.get("password"))


def send_platform_email_sync(to_addr: str, subject: str, body: str) -> dict[str, Any]:
    """Synchronous send via platform SMTP (safe for FastAPI BackgroundTasks)."""
    from app.services.integrations import _send_email_sync

    cfg = platform_smtp_config()
    if not cfg.get("host") or not cfg.get("password"):
        logger.error("Platform SMTP is not configured — cannot send mail to %s", to_addr)
        return {"ok": False, "detail": "Platform SMTP is not configured"}
    result = _send_email_sync(cfg, to_addr, subject, body)
    if not result.get("ok"):
        # Never log credentials; detail is exception text only
        logger.error("Platform email failed for %s: %s", to_addr, (result.get("detail") or "")[:300])
    else:
        logger.info("Platform email sent to %s", to_addr)
    return result
