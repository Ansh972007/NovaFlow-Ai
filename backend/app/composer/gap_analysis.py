"""Gap analysis against credential vault (+ legacy WorkspaceIntegration fallback)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import WorkspaceIntegration
from app.composer.chat_channels import get_channel_by_cap
from app.services import credential_vault as vault

# missing_label -> vault field key (within channel category/kind)
_LABEL_FIELDS: dict[str, str] = {
    "smtp_password": "smtp_password",
    "telegram_bot_token": "bot_token",
    "github_token": "token",
    "jira_api_token": "api_key",
    "linear_api_key": "api_key",
    "slack_webhook_url": "webhook_url",
    "discord_webhook_url": "webhook_url",
    "webhook_url": "webhook_url",
    "whatsapp_access_token": "access_token",
    "whatsapp_phone_number_id": "phone_number_id",
    "youtube_api_key": "api_key",
    "shopify_shop": "shop",
    "shopify_access_token": "access_token",
    "google_client_id": "client_id",
    "google_client_secret": "client_secret",
    "google_refresh_token": "refresh_token",
    "outlook_client_id": "client_id",
    "outlook_client_secret": "client_secret",
    "outlook_refresh_token": "refresh_token",
    "custom_api_key": "api_key",
    "openai_api_key": "api_key",
}

_NO_SECRET_CAPS = frozenset(
    {"cap_workflow", "cap_knowledge", "cap_agent", "cap_voice", "cap_ocr"}
)


def _vault_fields_for_category(
    db: Session, workspace_id: int, category: str, kind: str | None
) -> list[dict]:
    rows = vault.list_entries(db, workspace_id, category=category, kind=kind)
    if not rows and kind is not None:
        rows = vault.list_entries(db, workspace_id, category=category)
    out: list[dict] = []
    for row in rows:
        fields = vault.resolve_fields(
            db, workspace_id, category=row.category, kind=row.kind, credential_id=row.id
        )
        if fields:
            out.append(fields)
    return out


def _field_satisfied(category: str, fields: dict, field_key: str) -> bool:
    val = fields.get(field_key)
    if val is None or val == "":
        return False
    if category == "email" and field_key == "smtp_password":
        return bool(val)
    return bool(str(val).strip())


def _vault_has(db: Session, workspace_id: int, category: str, kind: str | None) -> bool:
    for fields in _vault_fields_for_category(db, workspace_id, category, kind):
        if category == "telegram" and fields.get("bot_token"):
            return True
        if category == "github" and fields.get("token"):
            return True
        if category == "jira" and fields.get("api_key"):
            return True
        if category == "slack" and (fields.get("webhook_url") or fields.get("bot_token")):
            return True
        if category == "discord" and fields.get("webhook_url"):
            return True
        if category == "email" and (fields.get("smtp_password") or fields.get("refresh_token")):
            return True
        if category == "linear" and fields.get("api_key"):
            return True
        if category == "webhook" and (fields.get("webhook_url") or fields.get("url")):
            return True
        if category == "custom" and (fields.get("api_key") or fields.get("token")):
            return True
        if category == "whatsapp" and fields.get("access_token"):
            return True
        if category == "youtube" and (fields.get("api_key") or fields.get("refresh_token")):
            return True
        if category == "shopify" and fields.get("access_token") and fields.get("shop"):
            return True
        if category == "google" and (
            fields.get("refresh_token") or fields.get("access_token") or fields.get("api_key")
        ):
            return True
        if category == "outlook" and (
            fields.get("refresh_token") or fields.get("access_token") or fields.get("client_secret")
        ):
            return True
        if category == "llm" and fields.get("api_key"):
            return True
    return False


def _missing_labels_for_channel(
    db: Session,
    workspace_id: int,
    channel,
    *,
    integration: WorkspaceIntegration | None,
) -> list[str]:
    if _vault_has(db, workspace_id, channel.category, channel.kind):
        return []
    if _legacy_has(integration, channel.cap):
        return []

    all_fields = _vault_fields_for_category(db, workspace_id, channel.category, channel.kind)
    missing: list[str] = []
    for label in channel.missing_labels:
        field_key = _LABEL_FIELDS.get(label, label.replace(f"{channel.id}_", "").replace("_", "_"))
        # Shopify: shop without token vs token without shop
        if label == "shopify_shop":
            has_shop = any(_field_satisfied("shopify", f, "shop") for f in all_fields)
            if not has_shop:
                missing.append(label)
            continue
        if label == "shopify_access_token":
            has_token = any(_field_satisfied("shopify", f, "access_token") for f in all_fields)
            if not has_token:
                missing.append(label)
            continue
        satisfied = any(_field_satisfied(channel.category, f, field_key) for f in all_fields)
        if not satisfied:
            missing.append(label)

    # Google/Outlook: api_key or refresh alone satisfies OAuth channel
    if not missing and channel.category in ("google", "outlook") and all_fields:
        return []
    if not missing and channel.cap == "cap_shopify" and not all_fields:
        return list(channel.missing_labels)

    return missing


def _legacy_has(integration: WorkspaceIntegration | None, cap: str) -> bool:
    if not integration:
        return False
    if cap == "cap_telegram":
        return bool(integration.telegram_bot_token_enc)
    if cap == "cap_github":
        return bool(integration.github_token_enc)
    if cap == "cap_jira":
        return bool(integration.jira_api_token_enc)
    if cap == "cap_slack":
        return bool(integration.slack_webhook_url_enc or integration.slack_bot_token_enc)
    if cap == "cap_discord":
        return bool(integration.discord_webhook_url_enc)
    if cap == "cap_smtp":
        return bool(integration.smtp_password_enc or integration.gmail_oauth_refresh_token_enc)
    return False


def analyze_solution_gaps(
    db: Session, workspace_id: int, required_capabilities: list[str]
) -> list[str]:
    """Return missing credential labels for required capabilities (channel-aware)."""
    missing: list[str] = []
    integration = (
        db.query(WorkspaceIntegration)
        .filter(WorkspaceIntegration.workspace_id == workspace_id)
        .first()
    )
    seen_caps: set[str] = set()

    for cap in required_capabilities:
        if cap in _NO_SECRET_CAPS or cap in seen_caps:
            continue
        seen_caps.add(cap)

        if cap == "cap_http":
            if _vault_has(db, workspace_id, "webhook", None) or _vault_has(
                db, workspace_id, "custom", "custom"
            ):
                continue
            missing.append("webhook_url")
            continue

        channel = get_channel_by_cap(cap)
        if channel:
            missing.extend(
                _missing_labels_for_channel(
                    db, workspace_id, channel, integration=integration
                )
            )
            continue

    return list(dict.fromkeys(missing))


def credential_slots_for_missing(missing_labels: list[str]) -> list[dict[str, str]]:
    """Friendly checklist rows for UI from missing label list."""
    from app.composer.chat_channels import friendly_missing_name

    slots: list[dict[str, str]] = []
    for label in missing_labels or []:
        field_key = _LABEL_FIELDS.get(label, "")
        slots.append(
            {
                "id": label,
                "label": friendly_missing_name(label),
                "field": field_key,
                "filled": False,
            }
        )
    return slots
