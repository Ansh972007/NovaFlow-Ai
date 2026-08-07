"""Multi-slot credentials vault — named secrets per workspace."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.composer.credentials import mask_credential, secure_vault_read, secure_vault_save
from app.crypto import decrypt_secret, encrypt_secret
from app.database import CredentialVaultEntry, LlmProvider

SECRET_FIELD_KEYS = {
    "api_key",
    "bot_token",
    "token",
    "password",
    "smtp_password",
    "webhook_url",
    "signing_secret",
    "refresh_token",
    "access_token",
    "client_secret",
    "private_key",
}

CATALOG: list[dict[str, Any]] = [
    {
        "category": "llm",
        "kind": "openai",
        "label": "OpenAI / compatible",
        "fields": [
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
            {"key": "base_url", "label": "Base URL", "secret": False, "required": False},
            {"key": "chat_model", "label": "Chat model", "secret": False, "required": False},
            {"key": "embedding_model", "label": "Embedding model", "secret": False, "required": False},
            {"key": "provider_type", "label": "Provider type", "secret": False, "required": False},
        ],
    },
    {
        "category": "email",
        "kind": "gmail_smtp",
        "label": "Gmail / SMTP",
        "fields": [
            {"key": "smtp_host", "label": "SMTP host", "secret": False, "required": True},
            {"key": "smtp_port", "label": "SMTP port", "secret": False, "required": False},
            {"key": "smtp_user", "label": "Username / email", "secret": False, "required": True},
            {"key": "smtp_password", "label": "Password / app password", "secret": True, "required": True},
            {"key": "smtp_from", "label": "From address", "secret": False, "required": False},
        ],
    },
    {
        "category": "email",
        "kind": "gmail_oauth",
        "label": "Gmail send (OAuth)",
        "setup": "guided",
        "oauth": True,
        "redirect_path": "/api/v1/integrations/gmail/oauth/callback",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        "fields": [
            {"key": "gmail_oauth_email", "label": "Connected email", "secret": False, "required": False},
        ],
        "advanced_fields": [
            {"key": "refresh_token", "label": "Refresh token (advanced)", "secret": True, "required": False},
            {"key": "access_token", "label": "Access token (advanced)", "secret": True, "required": False},
        ],
    },
    {
        "category": "telegram",
        "kind": "telegram_bot",
        "label": "Telegram bot",
        "fields": [
            {"key": "bot_token", "label": "Bot token", "secret": True, "required": True},
            {"key": "bot_username", "label": "Bot username", "secret": False, "required": False},
            {"key": "default_chat_id", "label": "Default chat ID", "secret": False, "required": False},
        ],
    },
    {
        "category": "slack",
        "kind": "slack_webhook",
        "label": "Slack webhook",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "secret": True, "required": True},
            {"key": "default_channel", "label": "Channel label", "secret": False, "required": False},
        ],
    },
    {
        "category": "slack",
        "kind": "slack_bot",
        "label": "Slack bot",
        "fields": [
            {"key": "bot_token", "label": "Bot token", "secret": True, "required": True},
            {"key": "signing_secret", "label": "Signing secret", "secret": True, "required": False},
        ],
    },
    {
        "category": "discord",
        "kind": "discord_webhook",
        "label": "Discord webhook",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "secret": True, "required": True},
            {"key": "default_channel", "label": "Channel label", "secret": False, "required": False},
        ],
    },
    {
        "category": "github",
        "kind": "github_pat",
        "label": "GitHub PAT",
        "fields": [
            {"key": "token", "label": "Personal access token", "secret": True, "required": True},
            {"key": "owner", "label": "Owner", "secret": False, "required": False},
            {"key": "repo", "label": "Repo", "secret": False, "required": False},
        ],
    },
    {
        "category": "jira",
        "kind": "jira_cloud",
        "label": "Jira Cloud",
        "fields": [
            {"key": "base_url", "label": "Site URL", "secret": False, "required": True},
            {"key": "email", "label": "Email", "secret": False, "required": True},
            {"key": "api_key", "label": "API token", "secret": True, "required": True},
        ],
    },
    {
        "category": "linear",
        "kind": "linear_api",
        "label": "Linear",
        "fields": [
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
            {"key": "team_id", "label": "Team ID", "secret": False, "required": False},
        ],
    },
    {
        "category": "webhook",
        "kind": "generic_webhook",
        "label": "Generic webhook",
        "fields": [
            {"key": "webhook_url", "label": "URL", "secret": True, "required": True},
        ],
    },
    {
        "category": "outlook",
        "kind": "microsoft_graph",
        "label": "Outlook / Microsoft Graph",
        "fields": [
            {"key": "tenant_id", "label": "Tenant ID", "secret": False, "required": False},
            {"key": "client_id", "label": "Client ID", "secret": False, "required": True},
            {"key": "client_secret", "label": "Client secret", "secret": True, "required": True},
            {"key": "refresh_token", "label": "Refresh token", "secret": True, "required": False},
            {"key": "access_token", "label": "Access token", "secret": True, "required": False},
            {"key": "mailbox", "label": "Mailbox email", "secret": False, "required": False},
        ],
        "oauth": True,
    },
    {
        "category": "google",
        "kind": "google_oauth",
        "label": "Google APIs (Calendar, Sheets, YouTube)",
        "setup": "manual",
        "oauth": True,
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        "fields": [
            {"key": "client_id", "label": "Client ID", "secret": False, "required": True},
            {"key": "client_secret", "label": "Client secret", "secret": True, "required": True},
            {"key": "refresh_token", "label": "Refresh token", "secret": True, "required": False},
            {"key": "access_token", "label": "Access token", "secret": True, "required": False},
            {"key": "api_key", "label": "API key (optional)", "secret": True, "required": False},
        ],
        "oauth": True,
    },
    {
        "category": "shopify",
        "kind": "shopify_admin",
        "label": "Shopify Admin API",
        "fields": [
            {"key": "shop", "label": "Shop domain (*.myshopify.com)", "secret": False, "required": True},
            {"key": "access_token", "label": "Admin API access token", "secret": True, "required": True},
            {"key": "api_version", "label": "API version", "secret": False, "required": False},
        ],
    },
    {
        "category": "whatsapp",
        "kind": "whatsapp_cloud",
        "label": "WhatsApp Cloud / Twilio",
        "fields": [
            {"key": "access_token", "label": "Access token", "secret": True, "required": True},
            {"key": "phone_number_id", "label": "Phone number ID", "secret": False, "required": True},
            {"key": "webhook_verify_token", "label": "Webhook verify token", "secret": True, "required": False},
        ],
    },
    {
        "category": "youtube",
        "kind": "youtube_api",
        "label": "YouTube Data API",
        "fields": [
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
            {"key": "channel_id", "label": "Channel ID", "secret": False, "required": False},
            {"key": "refresh_token", "label": "OAuth refresh token", "secret": True, "required": False},
        ],
    },
    {
        "category": "custom",
        "kind": "custom",
        "label": "Custom API / SaaS",
        "fields": [
            {"key": "api_key", "label": "API key / token", "secret": True, "required": True},
            {"key": "base_url", "label": "Base URL", "secret": False, "required": False},
            {"key": "notes", "label": "Notes", "secret": False, "required": False},
        ],
    },
]


def get_catalog() -> list[dict[str, Any]]:
    return CATALOG


def get_oauth_setup_info() -> dict[str, Any]:
    """Redirect URIs and console instructions for Google OAuth setup."""
    from app.config import GOOGLE_CLIENT_ID, OAUTH_REDIRECT_BASE
    from app.services.gmail_jira import GMAIL_SCOPES, gmail_redirect_uri, gmail_oauth_enabled
    from app.services.oauth import redirect_uri as login_redirect_uri

    base = (OAUTH_REDIRECT_BASE or "").rstrip("/")
    return {
        "google": {
            "platform_configured": bool(GOOGLE_CLIENT_ID),
            "gmail_oauth_enabled": gmail_oauth_enabled(),
            "console_url": "https://console.cloud.google.com/apis/credentials",
            "redirect_uris": [
                {
                    "id": "login",
                    "label": "Login (SSO)",
                    "uri": login_redirect_uri("google"),
                    "purpose": "User sign-in with Google",
                },
                {
                    "id": "gmail_send",
                    "label": "Gmail send (workflows)",
                    "uri": gmail_redirect_uri(),
                    "purpose": "Send email from workflows via Gmail API",
                },
            ],
            "scopes": {
                "login": ["openid", "email", "profile"],
                "gmail_send": [s for s in GMAIL_SCOPES.split(" ") if s],
                "google_apis": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/youtube.readonly",
                ],
            },
            "instructions": (
                "In Google Cloud Console → APIs & Services → Credentials → your OAuth client, "
                "add **both** Authorized redirect URIs below. For Gmail send, enable Gmail API and "
                "use Client ID + Client secret for Google APIs credentials, or Connect with Google "
                "for guided Gmail send."
            ),
            "oauth_redirect_base": base,
        },
    }


def validate_credential_fields(category: str, kind: str, fields: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Reject placeholder/hint values before vault save."""
    from app.composer.chat_channels import filter_real_credential_items, is_placeholder_credential_value

    clean = dict(fields or {})
    rejected: list[str] = []
    for key, val in list(clean.items()):
        if isinstance(val, str) and is_placeholder_credential_value(category, key, val):
            rejected.append(f"{key} looks like example/hint text")
            clean.pop(key, None)
    if not clean:
        return {}, rejected or ["No valid credential fields — paste real secrets, not examples"]
    items, more = filter_real_credential_items(
        [{"category": category, "kind": kind, "label": "default", "fields": clean}]
    )
    if not items:
        return {}, rejected + more
    return items[0].get("fields") or {}, rejected + more


def _encrypt_fields(fields: dict[str, Any]) -> str:
    return encrypt_secret(json.dumps(fields or {}))


def _decrypt_fields(enc: str) -> dict[str, Any]:
    if not enc:
        return {}
    try:
        raw = decrypt_secret(enc) or "{}"
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _public_meta(fields: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for k, v in (fields or {}).items():
        if k in SECRET_FIELD_KEYS or k.endswith("_token") or k.endswith("_password"):
            if isinstance(v, str) and v:
                meta[f"{k}_configured"] = True
                meta[f"{k}_mask"] = mask_credential(v)
            else:
                meta[f"{k}_configured"] = False
        else:
            meta[k] = v
    return meta


def serialize_entry(row: CredentialVaultEntry, *, include_secrets: bool = False) -> dict[str, Any]:
    fields = _decrypt_fields(row.fields_enc or "")
    try:
        public = json.loads(row.public_meta_json or "{}")
    except json.JSONDecodeError:
        public = {}
    if not public:
        public = _public_meta(fields)
    out = {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "category": row.category,
        "kind": row.kind,
        "label": row.label,
        "is_default": bool(row.is_default),
        "status": row.status or "unverified",
        "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "update_time": row.update_time.isoformat() if row.update_time else None,
        "meta": public,
    }
    if include_secrets:
        out["fields"] = fields
    else:
        # non-secret fields only
        safe = {k: v for k, v in fields.items() if k not in SECRET_FIELD_KEYS and not str(k).endswith("_token")}
        out["fields"] = safe
    return out


def list_entries(
    db: Session,
    workspace_id: int,
    *,
    category: str | None = None,
    kind: str | None = None,
) -> list[CredentialVaultEntry]:
    q = db.query(CredentialVaultEntry).filter(CredentialVaultEntry.workspace_id == workspace_id)
    if category:
        q = q.filter(CredentialVaultEntry.category == category)
    if kind:
        q = q.filter(CredentialVaultEntry.kind == kind)
    return q.order_by(CredentialVaultEntry.is_default.desc(), CredentialVaultEntry.update_time.desc()).all()


def get_entry(db: Session, workspace_id: int, entry_id: str) -> CredentialVaultEntry | None:
    row = db.get(CredentialVaultEntry, entry_id)
    if not row or row.workspace_id != workspace_id:
        return None
    return row


def _clear_defaults(db: Session, workspace_id: int, category: str, kind: str) -> None:
    rows = (
        db.query(CredentialVaultEntry)
        .filter(
            CredentialVaultEntry.workspace_id == workspace_id,
            CredentialVaultEntry.category == category,
            CredentialVaultEntry.kind == kind,
            CredentialVaultEntry.is_default == 1,
        )
        .all()
    )
    for r in rows:
        r.is_default = 0


def create_entry(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    category: str,
    kind: str,
    label: str,
    fields: dict[str, Any] | None = None,
    is_default: bool = False,
) -> CredentialVaultEntry:
    fields = dict(fields or {})
    label = (label or "default").strip()[:120] or "default"
    category = (category or "custom").strip()[:32]
    kind = (kind or "custom").strip()[:64]

    fields, rejected = validate_credential_fields(category, kind, fields)
    if rejected:
        raise ValueError("; ".join(rejected[:4]))
    if not fields:
        raise ValueError("No valid credential fields — paste real secrets, not examples")
    existing = (
        db.query(CredentialVaultEntry)
        .filter(
            CredentialVaultEntry.workspace_id == workspace_id,
            CredentialVaultEntry.category == category,
            CredentialVaultEntry.label == label,
        )
        .first()
    )
    if existing:
        # upsert same label
        return update_entry(
            db,
            existing,
            fields=fields,
            is_default=is_default if is_default else None,
            label=label,
        )

    if is_default:
        _clear_defaults(db, workspace_id, category, kind)
    elif not list_entries(db, workspace_id, category=category, kind=kind):
        is_default = True

    row = CredentialVaultEntry(
        workspace_id=workspace_id,
        user_id=user_id,
        category=category,
        kind=kind,
        label=label,
        fields_enc=_encrypt_fields(fields),
        public_meta_json=json.dumps(_public_meta(fields)),
        is_default=1 if is_default else 0,
        status="unverified",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _sync_legacy_defaults(db, row)
    return row


def update_entry(
    db: Session,
    row: CredentialVaultEntry,
    *,
    fields: dict[str, Any] | None = None,
    label: str | None = None,
    is_default: bool | None = None,
    status: str | None = None,
) -> CredentialVaultEntry:
    current = _decrypt_fields(row.fields_enc or "")
    if fields:
        merged = dict(current)
        for k, v in fields.items():
            if v is None or v == "":
                # skip empty secret updates (keep existing)
                if k in SECRET_FIELD_KEYS and merged.get(k):
                    continue
                if v == "" and k not in SECRET_FIELD_KEYS:
                    merged[k] = v
                continue
            merged[k] = v
        validated, rejected = validate_credential_fields(row.category, row.kind, merged)
        if rejected:
            raise ValueError("; ".join(rejected[:4]))
        if not validated:
            raise ValueError("No valid credential fields — paste real secrets, not examples")
        current = validated
        row.fields_enc = _encrypt_fields(current)
        row.public_meta_json = json.dumps(_public_meta(current))
    if label is not None:
        row.label = label.strip()[:120] or row.label
    if is_default is True:
        _clear_defaults(db, row.workspace_id, row.category, row.kind)
        row.is_default = 1
    elif is_default is False:
        row.is_default = 0
    if status:
        row.status = status[:24]
        if status == "ok":
            row.last_verified_at = datetime.utcnow()
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    _sync_legacy_defaults(db, row)
    return row


def delete_entry(db: Session, row: CredentialVaultEntry) -> None:
    was_default = bool(row.is_default)
    workspace_id = row.workspace_id
    category = row.category
    kind = row.kind
    db.delete(row)
    db.commit()
    if was_default:
        nxt = (
            db.query(CredentialVaultEntry)
            .filter(
                CredentialVaultEntry.workspace_id == workspace_id,
                CredentialVaultEntry.category == category,
                CredentialVaultEntry.kind == kind,
            )
            .order_by(CredentialVaultEntry.update_time.desc())
            .first()
        )
        if nxt:
            nxt.is_default = 1
            db.commit()


def set_default(db: Session, row: CredentialVaultEntry) -> CredentialVaultEntry:
    return update_entry(db, row, is_default=True)


def get_default(
    db: Session,
    workspace_id: int,
    *,
    category: str,
    kind: str | None = None,
) -> CredentialVaultEntry | None:
    q = db.query(CredentialVaultEntry).filter(
        CredentialVaultEntry.workspace_id == workspace_id,
        CredentialVaultEntry.category == category,
        CredentialVaultEntry.is_default == 1,
    )
    if kind:
        q = q.filter(CredentialVaultEntry.kind == kind)
    row = q.first()
    if row:
        return row
    q2 = db.query(CredentialVaultEntry).filter(
        CredentialVaultEntry.workspace_id == workspace_id,
        CredentialVaultEntry.category == category,
    )
    if kind:
        q2 = q2.filter(CredentialVaultEntry.kind == kind)
    return q2.order_by(CredentialVaultEntry.update_time.desc()).first()


def resolve_fields(
    db: Session,
    workspace_id: int | None,
    *,
    category: str,
    kind: str | None = None,
    credential_id: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        return {}
    row = None
    if credential_id:
        row = get_entry(db, workspace_id, credential_id)
    if not row:
        row = get_default(db, workspace_id, category=category, kind=kind)
    if not row:
        return {}
    return _decrypt_fields(row.fields_enc or "")


def upsert_from_chat(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    category: str,
    kind: str,
    label: str,
    fields: dict[str, Any],
) -> CredentialVaultEntry:
    label = (label or "default").strip()[:120] or "default"
    kind = (kind or "custom").strip()[:64] or "custom"
    category = (category or "custom").strip()[:32] or "custom"
    existing = (
        db.query(CredentialVaultEntry)
        .filter(
            CredentialVaultEntry.workspace_id == workspace_id,
            CredentialVaultEntry.category == category,
            CredentialVaultEntry.kind == kind,
            CredentialVaultEntry.label == label,
        )
        .first()
    )
    if not existing and label == "default":
        # Prefer default row of same category/kind
        existing = (
            db.query(CredentialVaultEntry)
            .filter(
                CredentialVaultEntry.workspace_id == workspace_id,
                CredentialVaultEntry.category == category,
                CredentialVaultEntry.kind == kind,
                CredentialVaultEntry.is_default == 1,
            )
            .first()
        )
    if existing:
        return update_entry(db, existing, fields=fields)
    return create_entry(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        category=category,
        kind=kind,
        label=label,
        fields=fields,
        is_default=label == "default",
    )


def _sync_legacy_defaults(db: Session, row: CredentialVaultEntry) -> None:
    """Keep legacy tables in sync for default vault entries (read fallbacks elsewhere)."""
    if not row.is_default:
        return
    fields = _decrypt_fields(row.fields_enc or "")
    try:
        from app.services import workspace_integrations as wi

        if row.category == "telegram" and fields.get("bot_token"):
            integ = wi.get_or_create(db, row.workspace_id)
            integ.telegram_bot_token_enc = secure_vault_save(fields["bot_token"])
            if fields.get("bot_username"):
                integ.telegram_bot_username = str(fields["bot_username"])[:64]
            if fields.get("default_chat_id"):
                integ.telegram_default_chat_id = str(fields["default_chat_id"])[:32]
            db.commit()
        elif row.category == "email" and row.kind == "gmail_smtp":
            integ = wi.get_or_create(db, row.workspace_id)
            if fields.get("smtp_host"):
                integ.smtp_host = str(fields["smtp_host"])[:255]
            if fields.get("smtp_port"):
                try:
                    integ.smtp_port = int(fields["smtp_port"])
                except (TypeError, ValueError):
                    pass
            if fields.get("smtp_user"):
                integ.smtp_user = str(fields["smtp_user"])[:255]
            if fields.get("smtp_password"):
                integ.smtp_password_enc = secure_vault_save(fields["smtp_password"])
            if fields.get("smtp_from"):
                integ.smtp_from = str(fields["smtp_from"])[:255]
            db.commit()
        elif row.category == "slack" and row.kind == "slack_webhook" and fields.get("webhook_url"):
            integ = wi.get_or_create(db, row.workspace_id)
            integ.slack_webhook_url_enc = secure_vault_save(fields["webhook_url"])
            if fields.get("default_channel"):
                integ.slack_default_channel = str(fields["default_channel"])[:120]
            db.commit()
        elif row.category == "discord" and fields.get("webhook_url"):
            integ = wi.get_or_create(db, row.workspace_id)
            integ.discord_webhook_url_enc = secure_vault_save(fields["webhook_url"])
            db.commit()
        elif row.category == "github" and fields.get("token"):
            integ = wi.get_or_create(db, row.workspace_id)
            integ.github_token_enc = secure_vault_save(fields["token"])
            if fields.get("owner"):
                integ.github_owner = str(fields["owner"])[:120]
            if fields.get("repo"):
                integ.github_repo = str(fields["repo"])[:120]
            db.commit()
        elif row.category == "llm" and fields.get("api_key"):
            # Mirror into llm_providers as an active-capable row
            name = f"Vault: {row.label}"
            provider = (
                db.query(LlmProvider)
                .filter(LlmProvider.name == name)
                .first()
            )
            ptype = (fields.get("provider_type") or "openai").strip() or "openai"
            if not provider:
                provider = LlmProvider(
                    name=name,
                    provider_type=ptype,
                    base_url=(fields.get("base_url") or "")[:512],
                    api_key_enc=encrypt_secret(fields["api_key"]),
                    chat_model=(fields.get("chat_model") or "")[:120],
                    embedding_model=(fields.get("embedding_model") or "")[:120],
                    is_active=1,
                )
                db.add(provider)
            else:
                provider.provider_type = ptype
                provider.base_url = (fields.get("base_url") or provider.base_url or "")[:512]
                provider.api_key_enc = encrypt_secret(fields["api_key"])
                if fields.get("chat_model"):
                    provider.chat_model = str(fields["chat_model"])[:120]
                if fields.get("embedding_model"):
                    provider.embedding_model = str(fields["embedding_model"])[:120]
            db.commit()
    except Exception:
        db.rollback()


def overview(db: Session, workspace_id: int) -> dict[str, Any]:
    rows = list_entries(db, workspace_id)
    by_cat: dict[str, int] = {}
    defaults: dict[str, str] = {}
    for r in rows:
        by_cat[r.category] = by_cat.get(r.category, 0) + 1
        if r.is_default:
            defaults[f"{r.category}:{r.kind}"] = r.label
    return {
        "total": len(rows),
        "by_category": by_cat,
        "defaults": defaults,
        "missing_suggested": [
            c
            for c in ("llm", "email", "telegram")
            if c not in by_cat
        ],
    }
