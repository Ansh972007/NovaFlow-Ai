"""ECP authentication framework."""

from __future__ import annotations

from typing import Any

SUPPORTED_AUTH_TYPES = [
    "oauth2",
    "oauth_pkce",
    "api_key",
    "jwt",
    "bearer",
    "pat",
    "basic",
    "saml",
    "oidc",
    "aws_iam",
    "azure_identity",
    "gcp_iam",
    "webhook",
    "bot_token",
    "none",
]


def validate_auth_config(auth_type: str, config: dict | None = None) -> dict[str, Any]:
    config = config or {}
    auth_type = (auth_type or "api_key").lower()
    if auth_type not in SUPPORTED_AUTH_TYPES:
        return {"valid": False, "error": f"Unsupported auth type: {auth_type}"}
    required = {
        "oauth2": ["client_id", "client_secret"],
        "oauth_pkce": ["client_id"],
        "api_key": ["api_key"],
        "basic": ["username", "password"],
        "pat": ["token"],
        "bearer": ["token"],
        "webhook": ["url"],
        "bot_token": ["token"],
    }.get(auth_type, [])
    missing = [k for k in required if not config.get(k)]
    return {"valid": not missing, "auth_type": auth_type, "missing": missing}


def auth_headers(auth_type: str, secret: str, config: dict | None = None) -> dict[str, str]:
    config = config or {}
    auth_type = (auth_type or "api_key").lower()
    if auth_type in ("bearer", "pat", "bot_token", "jwt"):
        return {"Authorization": f"Bearer {secret}"}
    if auth_type == "api_key" and config.get("header"):
        return {config["header"]: secret}
    if auth_type == "basic":
        import base64

        user = config.get("username") or ""
        token = base64.b64encode(f"{user}:{secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
    return {}
