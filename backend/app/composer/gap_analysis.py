"""Gap analysis against credential vault (+ legacy WorkspaceIntegration fallback)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import WorkspaceIntegration
from app.services import credential_vault as vault

# capability -> (category, kind, missing_label)
_CAP_REQUIREMENTS: dict[str, tuple[str, str | None, str]] = {
    "cap_telegram": ("telegram", "telegram_bot", "telegram_bot_token"),
    "cap_github": ("github", "github_pat", "github_token"),
    "cap_jira": ("jira", "jira_cloud", "jira_api_token"),
    "cap_linear": ("linear", "linear_api", "linear_api_key"),
    "cap_slack": ("slack", None, "slack_webhook_url"),
    "cap_discord": ("discord", "discord_webhook", "discord_webhook_url"),
    "cap_smtp": ("email", None, "smtp_password"),
    "cap_http": ("webhook", None, "webhook_url"),
    "cap_whatsapp": ("whatsapp", "whatsapp_cloud", "whatsapp_access_token"),
    "cap_youtube": ("youtube", "youtube_api", "youtube_api_key"),
    "cap_shopify": ("shopify", "shopify_admin", "shopify_access_token"),
    "cap_google": ("google", "google_oauth", "google_refresh_token"),
    "cap_outlook": ("outlook", "microsoft_graph", "outlook_refresh_token"),
    "cap_llm": ("llm", "openai", "openai_api_key"),
}


def _vault_has(db: Session, workspace_id: int, category: str, kind: str | None) -> bool:
    rows = vault.list_entries(db, workspace_id, category=category, kind=kind)
    if not rows:
        if kind is None:
            rows = vault.list_entries(db, workspace_id, category=category)
        else:
            # also try category-only (UI may use a sibling kind)
            rows = vault.list_entries(db, workspace_id, category=category)
            if not rows:
                return False
    for row in rows:
        fields = vault.resolve_fields(
            db, workspace_id, category=row.category, kind=row.kind, credential_id=row.id
        )
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
    """Return missing credential labels for required capabilities."""
    missing: list[str] = []
    integration = (
        db.query(WorkspaceIntegration)
        .filter(WorkspaceIntegration.workspace_id == workspace_id)
        .first()
    )

    for cap in required_capabilities:
        # Caps that never need external secrets
        if cap in ("cap_workflow", "cap_knowledge", "cap_agent", "cap_voice", "cap_ocr"):
            continue
        # HTTP satisfied by webhook URL OR custom API key
        if cap == "cap_http":
            if _vault_has(db, workspace_id, "webhook", None) or _vault_has(
                db, workspace_id, "custom", "custom"
            ):
                continue
            missing.append("webhook_url")
            continue
        req = _CAP_REQUIREMENTS.get(cap)
        if not req:
            continue
        category, kind, label = req
        if _vault_has(db, workspace_id, category, kind):
            continue
        if _legacy_has(integration, cap):
            continue
        if cap == "cap_shopify":
            rows = vault.list_entries(db, workspace_id, category="shopify")
            shop_only = False
            for row in rows:
                fields = vault.resolve_fields(
                    db, workspace_id, category=row.category, kind=row.kind, credential_id=row.id
                )
                if fields.get("access_token") and not fields.get("shop"):
                    missing.append("shopify_shop")
                    shop_only = True
                    break
            if not shop_only:
                missing.append(label)
            continue
        missing.append(label)

    return list(dict.fromkeys(missing))
