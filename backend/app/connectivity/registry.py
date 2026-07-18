"""ECP connector registry — catalog of supported connector types."""

from __future__ import annotations

from typing import Any

CONNECTOR_CATALOG: dict[str, dict[str, Any]] = {
    # Cloud storage
    "s3": {"category": "cloud_storage", "auth": ["aws_iam", "api_key"], "capabilities": ["read", "write", "sync"]},
    "azure_blob": {"category": "cloud_storage", "auth": ["azure_identity", "api_key"], "capabilities": ["read", "write", "sync"]},
    "gcs": {"category": "cloud_storage", "auth": ["gcp_iam", "api_key"], "capabilities": ["read", "write", "sync"]},
    "dropbox": {"category": "cloud_storage", "auth": ["oauth2", "bearer"], "capabilities": ["read", "write", "sync"]},
    "gdrive": {"category": "cloud_storage", "auth": ["oauth2", "bearer"], "capabilities": ["read", "write", "sync"]},
    "onedrive": {"category": "cloud_storage", "auth": ["oauth2", "bearer"], "capabilities": ["read", "write", "sync"]},
    "sharepoint": {"category": "cloud_storage", "auth": ["oauth2", "bearer"], "capabilities": ["read", "write", "sync"]},
    "git": {"category": "development", "auth": ["pat", "none"], "capabilities": ["clone", "read", "sync"]},
    # Communication
    "slack": {"category": "communication", "auth": ["oauth2", "webhook", "bot_token"], "capabilities": ["notify", "webhook", "events"]},
    "discord": {"category": "communication", "auth": ["webhook"], "capabilities": ["notify"]},
    "telegram": {"category": "communication", "auth": ["bot_token"], "capabilities": ["notify", "webhook"]},
    "email_smtp": {"category": "communication", "auth": ["basic", "oauth2"], "capabilities": ["send"]},
    "twilio": {"category": "communication", "auth": ["api_key"], "capabilities": ["sms", "voice"]},
    # Development
    "github": {"category": "development", "auth": ["pat", "oauth2"], "capabilities": ["issues", "repos", "webhook"]},
    "gitlab": {"category": "development", "auth": ["pat", "oauth2"], "capabilities": ["issues", "repos"]},
    "bitbucket": {"category": "development", "auth": ["pat", "oauth2"], "capabilities": ["repos"]},
    "jira": {"category": "development", "auth": ["api_key", "oauth2"], "capabilities": ["issues", "webhook"]},
    "linear": {"category": "development", "auth": ["api_key"], "capabilities": ["issues"]},
    # CRM
    "salesforce": {"category": "crm", "auth": ["oauth2"], "capabilities": ["crm", "sync"]},
    "hubspot": {"category": "crm", "auth": ["oauth2", "api_key"], "capabilities": ["crm", "sync"]},
    # Databases
    "postgresql": {"category": "database", "auth": ["basic", "jwt"], "capabilities": ["query", "sync"]},
    "mysql": {"category": "database", "auth": ["basic"], "capabilities": ["query", "sync"]},
    "mongodb": {"category": "database", "auth": ["basic", "api_key"], "capabilities": ["query", "sync"]},
    "redis": {"category": "database", "auth": ["basic", "api_key"], "capabilities": ["cache", "streams"]},
    "snowflake": {"category": "database", "auth": ["jwt", "basic"], "capabilities": ["query", "sync"]},
    # AI providers
    "openai": {"category": "ai_provider", "auth": ["api_key", "bearer"], "capabilities": ["chat", "embeddings"]},
    "anthropic": {"category": "ai_provider", "auth": ["api_key"], "capabilities": ["chat"]},
    "openrouter": {"category": "ai_provider", "auth": ["api_key"], "capabilities": ["chat", "embeddings"]},
    "ollama": {"category": "ai_provider", "auth": ["none"], "capabilities": ["chat", "embeddings"]},
    # Identity
    "okta": {"category": "identity", "auth": ["oauth2", "oidc"], "capabilities": ["auth"]},
    "azure_ad": {"category": "identity", "auth": ["oauth2", "oidc"], "capabilities": ["auth"]},
    # Observability
    "grafana": {"category": "observability", "auth": ["api_key", "basic"], "capabilities": ["metrics", "alerts"]},
    "datadog": {"category": "observability", "auth": ["api_key"], "capabilities": ["metrics", "events"]},
    # MCP
    "mcp_server": {"category": "mcp", "auth": ["none", "bearer", "oauth2"], "capabilities": ["tools", "resources", "streaming"]},
    "mcp_client": {"category": "mcp", "auth": ["none", "bearer"], "capabilities": ["discover", "invoke"]},
}


def list_connectors(*, category: str = "") -> list[dict[str, Any]]:
    rows = []
    for ctype, meta in CONNECTOR_CATALOG.items():
        if category and meta.get("category") != category:
            continue
        rows.append({"type": ctype, **meta})
    return sorted(rows, key=lambda r: r["type"])


def get_connector_meta(connector_type: str) -> dict[str, Any] | None:
    meta = CONNECTOR_CATALOG.get(connector_type)
    if not meta:
        return None
    return {"type": connector_type, **meta}


def connector_matrix() -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {}
    for ctype, meta in CONNECTOR_CATALOG.items():
        cat = meta.get("category") or "other"
        matrix.setdefault(cat, []).append(ctype)
    return matrix
