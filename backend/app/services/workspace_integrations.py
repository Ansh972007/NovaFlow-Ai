from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TELEGRAM_BOT_TOKEN,
)
from app.crypto import decrypt_secret, encrypt_secret
from app.database import WorkspaceIntegration


def _mask_secret(value: str) -> str:
    """Opaque mask — never reveal password characters to API clients."""
    if not value:
        return ""
    return "••••••••"


def get_or_create(db: Session, workspace_id: int) -> WorkspaceIntegration:
    row = db.get(WorkspaceIntegration, workspace_id)
    if not row:
        row = WorkspaceIntegration(workspace_id=workspace_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _gmail_oauth_enabled(db: Session, workspace_id: int) -> bool:
    try:
        from app.services.gmail_jira import gmail_oauth_enabled_for_workspace

        return bool(gmail_oauth_enabled_for_workspace(db, workspace_id))
    except Exception:
        return False


def resolve_telegram_token(
    db: Session,
    workspace_id: int | None,
    override: str = "",
    *,
    credential_id: str | None = None,
) -> str:
    if override:
        return override.strip()
    if workspace_id:
        try:
            from app.services import credential_vault as vault

            fields = vault.resolve_fields(
                db,
                workspace_id,
                category="telegram",
                kind="telegram_bot",
                credential_id=credential_id,
            )
            token = "".join(str(fields.get("bot_token") or "").split())
            if token:
                return token
        except Exception:
            pass
        row = db.get(WorkspaceIntegration, workspace_id)
        if row and row.telegram_bot_token_enc:
            token = decrypt_secret(row.telegram_bot_token_enc)
            if token:
                return "".join(str(token).split())
    raw_env = (TELEGRAM_BOT_TOKEN or "").strip()
    return "".join(str(raw_env).split())
def resolve_telegram_chat_id(
    db: Session,
    workspace_id: int | None,
    override: str = "",
    *,
    credential_id: str | None = None,
) -> str:
    if override and override.strip() and override.strip() != "{{chat_id}}":
        return override.strip()
    if workspace_id:
        try:
            from app.services import credential_vault as vault

            fields = vault.resolve_fields(
                db,
                workspace_id,
                category="telegram",
                kind="telegram_bot",
                credential_id=credential_id,
            )
            cid = (fields.get("default_chat_id") or fields.get("chat_id") or "").strip()
            if cid:
                return cid
        except Exception:
            pass
        row = db.get(WorkspaceIntegration, workspace_id)
        if row and row.telegram_default_chat_id:
            return row.telegram_default_chat_id.strip()
    return ""


def resolve_smtp_config(
    db: Session,
    workspace_id: int | None,
    *,
    credential_id: str | None = None,
) -> dict[str, Any]:
    host = SMTP_HOST
    port = SMTP_PORT
    user = SMTP_USER
    password = SMTP_PASSWORD
    from_addr = SMTP_FROM

    if workspace_id:
        try:
            from app.services import credential_vault as vault

            fields = vault.resolve_fields(
                db,
                workspace_id,
                category="email",
                kind=None,
                credential_id=credential_id,
            )
            if fields:
                if fields.get("smtp_host"):
                    host = fields["smtp_host"]
                if fields.get("smtp_port"):
                    try:
                        port = int(fields["smtp_port"])
                    except (TypeError, ValueError):
                        pass
                if fields.get("smtp_user"):
                    user = fields["smtp_user"]
                if fields.get("smtp_password"):
                    password = fields["smtp_password"]
                if fields.get("smtp_from"):
                    from_addr = fields["smtp_from"]
                cfg = {
                    "host": (host or "").strip(),
                    "port": port or 587,
                    "user": (user or "").strip(),
                    "password": password or "",
                    "from_addr": (from_addr or user or "novaflow@localhost").strip(),
                    "credential_id": credential_id,
                }
                # Incomplete vault entry → keep falling through to platform SMTP
                if cfg["host"] and cfg["password"]:
                    return cfg
        except Exception:
            pass
        row = db.get(WorkspaceIntegration, workspace_id)
        if row:
            if row.smtp_host:
                host = row.smtp_host
            if row.smtp_port:
                port = int(row.smtp_port)
            if row.smtp_user:
                user = row.smtp_user
            if row.smtp_password_enc:
                password = decrypt_secret(row.smtp_password_enc) or password
            if row.smtp_from:
                from_addr = row.smtp_from

    # Ensure platform defaults fill any gaps
    if not host or not password:
        from app.services.platform_mail import platform_smtp_config

        plat = platform_smtp_config()
        host = host or plat.get("host") or ""
        port = port or plat.get("port") or 587
        user = user or plat.get("user") or ""
        password = password or plat.get("password") or ""
        from_addr = from_addr or plat.get("from_addr") or ""

    return {
        "host": (host or "").strip(),
        "port": port or 587,
        "user": (user or "").strip(),
        "password": password or "",
        "from_addr": (from_addr or user or "novaflow@localhost").strip(),
    }


def email_ready(db: Session, workspace_id: int) -> bool:
    from app.services.platform_mail import platform_mail_ready

    row = db.get(WorkspaceIntegration, workspace_id)
    if row and (row.gmail_auth_mode or "smtp") == "oauth" and row.gmail_oauth_refresh_token_enc:
        return True
    smtp = resolve_smtp_config(db, workspace_id)
    if bool(smtp.get("host") and smtp.get("password") and (smtp.get("user") or smtp.get("from_addr"))):
        return True
    return platform_mail_ready()


def resolve_slack_webhook(
    db: Session,
    workspace_id: int | None,
    override: str = "",
    *,
    credential_id: str | None = None,
) -> str:
    if override:
        return override.strip()
    if workspace_id:
        try:
            from app.services import credential_vault as vault

            fields = vault.resolve_fields(
                db,
                workspace_id,
                category="slack",
                kind="slack_webhook",
                credential_id=credential_id,
            )
            url = (fields.get("webhook_url") or "").strip()
            if url:
                return url
        except Exception:
            pass
        row = db.get(WorkspaceIntegration, workspace_id)
        if row and row.slack_webhook_url_enc:
            return decrypt_secret(row.slack_webhook_url_enc) or ""
    return ""


def resolve_discord_webhook(
    db: Session,
    workspace_id: int | None,
    override: str = "",
    *,
    credential_id: str | None = None,
) -> str:
    if override:
        return override.strip()
    if workspace_id:
        try:
            from app.services import credential_vault as vault

            fields = vault.resolve_fields(
                db,
                workspace_id,
                category="discord",
                kind="discord_webhook",
                credential_id=credential_id,
            )
            url = (fields.get("webhook_url") or "").strip()
            if url:
                return url
        except Exception:
            pass
        row = db.get(WorkspaceIntegration, workspace_id)
        if row and getattr(row, "discord_webhook_url_enc", None):
            return decrypt_secret(row.discord_webhook_url_enc) or ""
    return ""


def slack_ready(db: Session, workspace_id: int) -> bool:
    return bool(resolve_slack_webhook(db, workspace_id))


def discord_ready(db: Session, workspace_id: int) -> bool:
    return bool(resolve_discord_webhook(db, workspace_id))


def integrations_dict(db: Session, workspace_id: int) -> dict:
    from app.services.gmail_jira import gmail_oauth_enabled, resolve_jira_config
    from app.services.github_issues import resolve_github_config
    from app.services.linear_issues import resolve_linear_config

    row = get_or_create(db, workspace_id)
    token = decrypt_secret(row.telegram_bot_token_enc or "")
    password = decrypt_secret(row.smtp_password_enc or "")
    smtp = resolve_smtp_config(db, workspace_id)
    oauth_connected = bool(row.gmail_oauth_refresh_token_enc)
    auth_mode = (row.gmail_auth_mode or "smtp").strip().lower()
    if oauth_connected and auth_mode != "oauth":
        auth_mode = "oauth"
    jira_token = decrypt_secret(row.jira_api_token_enc or "") if row.jira_api_token_enc else ""
    jira = resolve_jira_config(db, workspace_id)
    slack_url = decrypt_secret(row.slack_webhook_url_enc or "") if row.slack_webhook_url_enc else ""
    discord_url = (
        decrypt_secret(row.discord_webhook_url_enc or "") if getattr(row, "discord_webhook_url_enc", None) else ""
    )
    github = resolve_github_config(db, workspace_id)
    gh_token = github.get("token") or ""
    linear = resolve_linear_config(db, workspace_id)
    linear_key = linear.get("api_key") or ""
    slack_bot = decrypt_secret(row.slack_bot_token_enc or "") if getattr(row, "slack_bot_token_enc", None) else ""
    slack_signing = (
        decrypt_secret(row.slack_signing_secret_enc or "") if getattr(row, "slack_signing_secret_enc", None) else ""
    )

    return {
        "workspace_id": workspace_id,
        "public_base_url": row.public_base_url or "",
        "telegram": {
            "configured": bool(token or TELEGRAM_BOT_TOKEN),
            "bot_token_masked": _mask_secret(token) if token else ("" if not TELEGRAM_BOT_TOKEN else "env"),
            "bot_username": row.telegram_bot_username or "",
            "default_chat_id": row.telegram_default_chat_id or "",
            "source": "workspace" if token else ("env" if TELEGRAM_BOT_TOKEN else "none"),
            "webhook_workflow_id": row.telegram_webhook_workflow_id or "",
            "webhook_url": row.telegram_webhook_url or "",
            "webhook_registered_at": row.telegram_webhook_registered_at.isoformat()
            if row.telegram_webhook_registered_at
            else None,
        },
        "email": {
            "configured": email_ready(db, workspace_id),
            "gmail_preset": bool(row.gmail_preset),
            "auth_mode": auth_mode,
            "smtp_host": row.smtp_host or smtp.get("host") or "",
            "smtp_port": row.smtp_port or smtp.get("port") or 587,
            "smtp_user": row.smtp_user or smtp.get("user") or "",
            "smtp_from": row.smtp_from or smtp.get("from_addr") or "",
            "smtp_password_masked": (
                _mask_secret(password)
                if password
                else ("••••configured" if SMTP_PASSWORD else "")
            ),
            # Never expose whether env password equals a known value — boolean only
            "smtp_password_configured": bool(password or SMTP_PASSWORD),
            "source": "oauth"
            if oauth_connected and auth_mode == "oauth"
            else ("workspace" if row.smtp_host or row.smtp_user else ("env" if SMTP_HOST else "none")),
            "oauth_enabled": _gmail_oauth_enabled(db, workspace_id),
            "oauth_connected": oauth_connected,
            "oauth_email": row.gmail_oauth_email or "",
            "oauth_connected_at": row.gmail_oauth_connected_at.isoformat() if row.gmail_oauth_connected_at else None,
        },
        "jira": {
            "configured": jira["configured"],
            "base_url": row.jira_base_url or "",
            "email": row.jira_email or "",
            "api_token_masked": _mask_secret(jira_token) if jira_token else "",
            "source": "workspace" if jira_token else "none",
        },
        "slack": {
            "configured": bool(slack_url),
            "webhook_url_masked": _mask_secret(slack_url) if slack_url else "",
            "default_channel": row.slack_default_channel or "",
            "source": "workspace" if slack_url else "none",
            "bot_token_masked": _mask_secret(slack_bot) if slack_bot else "",
            "signing_secret_masked": _mask_secret(slack_signing) if slack_signing else "",
            "bot_configured": bool(slack_bot and slack_signing),
            "events_workflow_id": getattr(row, "slack_events_workflow_id", None) or "",
            "events_url": getattr(row, "slack_events_url", None) or "",
            "events_registered_at": row.slack_events_registered_at.isoformat()
            if getattr(row, "slack_events_registered_at", None)
            else None,
        },
        "discord": {
            "configured": bool(discord_url),
            "webhook_url_masked": _mask_secret(discord_url) if discord_url else "",
            "default_channel": getattr(row, "discord_default_channel", None) or "",
            "source": "workspace" if discord_url else "none",
        },
        "github": {
            "configured": github["configured"],
            "token_masked": _mask_secret(gh_token) if gh_token else "",
            "owner": row.github_owner or "",
            "repo": row.github_repo or "",
            "default_repo": github.get("default_repo") or "",
            "source": "workspace" if gh_token else "none",
        },
        "linear": {
            "configured": linear["configured"],
            "api_key_masked": _mask_secret(linear_key) if linear_key else "",
            "team_id": getattr(row, "linear_team_id", None) or "",
            "source": "workspace" if linear_key else "none",
        },
    }


def update_integrations(db: Session, workspace_id: int, body: dict) -> dict:
    row = get_or_create(db, workspace_id)

    if "public_base_url" in body:
        row.public_base_url = str(body.get("public_base_url") or "").strip()[:500]

    tg = body.get("telegram") if isinstance(body.get("telegram"), dict) else {}
    if tg:
        if "bot_username" in tg:
            row.telegram_bot_username = str(tg.get("bot_username") or "").strip()[:64]
        if "default_chat_id" in tg:
            row.telegram_default_chat_id = str(tg.get("default_chat_id") or "").strip()[:32]
        if "bot_token" in tg:
            token = str(tg.get("bot_token") or "").strip()
            if token:
                row.telegram_bot_token_enc = encrypt_secret(token)
            elif tg.get("clear_token"):
                row.telegram_bot_token_enc = ""

    email = body.get("email") if isinstance(body.get("email"), dict) else {}
    if email:
        if "auth_mode" in email:
            mode = str(email.get("auth_mode") or "smtp").strip().lower()
            row.gmail_auth_mode = "oauth" if mode == "oauth" else "smtp"
        if "gmail_preset" in email:
            row.gmail_preset = 1 if email.get("gmail_preset") else 0
            if row.gmail_preset:
                row.smtp_host = "smtp.gmail.com"
                row.smtp_port = 587
        if "smtp_host" in email:
            row.smtp_host = str(email.get("smtp_host") or "").strip()[:255]
        if "smtp_port" in email:
            row.smtp_port = max(1, min(65535, int(email.get("smtp_port") or 587)))
        if "smtp_user" in email:
            row.smtp_user = str(email.get("smtp_user") or "").strip()[:255]
        if "smtp_from" in email:
            row.smtp_from = str(email.get("smtp_from") or "").strip()[:255]
        if "smtp_password" in email:
            pwd = str(email.get("smtp_password") or "").strip()
            if pwd:
                row.smtp_password_enc = encrypt_secret(pwd)
            elif email.get("clear_password"):
                row.smtp_password_enc = ""

    jira = body.get("jira") if isinstance(body.get("jira"), dict) else {}
    if jira:
        if "base_url" in jira:
            row.jira_base_url = str(jira.get("base_url") or "").strip().rstrip("/")[:500]
        if "email" in jira:
            row.jira_email = str(jira.get("email") or "").strip()[:255]
        if "api_token" in jira:
            tok = str(jira.get("api_token") or "").strip()
            if tok:
                row.jira_api_token_enc = encrypt_secret(tok)
        if jira.get("clear_token"):
            row.jira_api_token_enc = ""

    slack = body.get("slack") if isinstance(body.get("slack"), dict) else {}
    if slack:
        if "default_channel" in slack:
            row.slack_default_channel = str(slack.get("default_channel") or "").strip()[:120]
        if "webhook_url" in slack:
            url = str(slack.get("webhook_url") or "").strip()
            if url:
                row.slack_webhook_url_enc = encrypt_secret(url)
        if slack.get("clear_webhook"):
            row.slack_webhook_url_enc = ""
        if "bot_token" in slack:
            tok = str(slack.get("bot_token") or "").strip()
            if tok:
                row.slack_bot_token_enc = encrypt_secret(tok)
        if slack.get("clear_bot_token"):
            row.slack_bot_token_enc = ""
        if "signing_secret" in slack:
            sec = str(slack.get("signing_secret") or "").strip()
            if sec:
                row.slack_signing_secret_enc = encrypt_secret(sec)
        if slack.get("clear_signing_secret"):
            row.slack_signing_secret_enc = ""

    discord = body.get("discord") if isinstance(body.get("discord"), dict) else {}
    if discord:
        if "default_channel" in discord:
            row.discord_default_channel = str(discord.get("default_channel") or "").strip()[:120]
        if "webhook_url" in discord:
            url = str(discord.get("webhook_url") or "").strip()
            if url:
                row.discord_webhook_url_enc = encrypt_secret(url)
        if discord.get("clear_webhook"):
            row.discord_webhook_url_enc = ""

    github = body.get("github") if isinstance(body.get("github"), dict) else {}
    if github:
        if "owner" in github:
            row.github_owner = str(github.get("owner") or "").strip()[:120]
        if "repo" in github:
            row.github_repo = str(github.get("repo") or "").strip()[:120]
        if "token" in github:
            tok = str(github.get("token") or "").strip()
            if tok:
                row.github_token_enc = encrypt_secret(tok)
        if github.get("clear_token"):
            row.github_token_enc = ""

    linear = body.get("linear") if isinstance(body.get("linear"), dict) else {}
    if linear:
        if "team_id" in linear:
            row.linear_team_id = str(linear.get("team_id") or "").strip()[:64]
        if "api_key" in linear:
            tok = str(linear.get("api_key") or "").strip()
            if tok:
                row.linear_api_key_enc = encrypt_secret(tok)
        if linear.get("clear_api_key"):
            row.linear_api_key_enc = ""

    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return integrations_dict(db, workspace_id)


def record_telegram_webhook(
    db: Session,
    workspace_id: int,
    workflow_id: str,
    webhook_url: str,
) -> None:
    row = get_or_create(db, workspace_id)
    row.telegram_webhook_workflow_id = workflow_id[:32]
    row.telegram_webhook_url = webhook_url[:500]
    row.telegram_webhook_registered_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.commit()


def record_slack_events(
    db: Session,
    workspace_id: int,
    workflow_id: str,
    events_url: str,
) -> None:
    row = get_or_create(db, workspace_id)
    row.slack_events_workflow_id = workflow_id[:32]
    row.slack_events_url = events_url[:500]
    row.slack_events_registered_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.commit()


def resolve_public_base_url(db: Session, workspace_id: int, override: str = "") -> str:
    if override:
        return override.rstrip("/")
    row = db.get(WorkspaceIntegration, workspace_id)

    # Check live Ngrok status
    active_ngrok = ""
    try:
        import httpx

        for api_url in ("http://host.docker.internal:4040/api/tunnels", "http://127.0.0.1:4040/api/tunnels"):
            try:
                res = httpx.get(api_url, timeout=1.5)
                if res.status_code == 200:
                    data = res.json()
                    for t in data.get("tunnels", []):
                        purl = (t.get("public_url") or "").strip().rstrip("/")
                        if purl.startswith("https://"):
                            active_ngrok = purl
                            if row and row.public_base_url != purl:
                                row.public_base_url = purl
                                db.commit()
                            break
            except Exception:
                pass
            if active_ngrok:
                break
    except Exception:
        pass

    if active_ngrok:
        return active_ngrok

    if row and row.public_base_url and "ngrok" not in row.public_base_url.lower():
        return row.public_base_url.rstrip("/")

    from app.config import PORT, PUBLIC_BASE_URL

    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/")

    return f"http://localhost:{PORT}"


def apply_public_base_from_env(db: Session) -> str | None:
    """Sync NOVAFLOW_PUBLIC_BASE_URL from env into all workspace integration rows."""
    from app.config import PUBLIC_BASE_URL

    base = (PUBLIC_BASE_URL or "").strip().rstrip("/")
    if not base:
        return None
    rows = db.query(WorkspaceIntegration).all()
    if not rows:
        return base
    for row in rows:
        if row.public_base_url != base:
            row.public_base_url = base[:500]
            row.updated_at = datetime.utcnow()
    db.commit()
    return base
