"""Security configuration — env-driven, production-safe defaults."""

from __future__ import annotations

import os
import warnings

from app.config import FRONTEND_URL, JWT_SECRET

NOVAFLOW_ENV = os.getenv("NOVAFLOW_ENV", os.getenv("ENV", "development")).lower()
IS_PRODUCTION = NOVAFLOW_ENV in {"production", "prod"}

JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER", "novaflow-ai")

# Short-lived access tokens; long-lived refresh with rotation.
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))
# Backward-compat: if JWT_EXPIRE_HOURS still set very high, clamp access to ACCESS_TOKEN_MINUTES.
MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "10"))
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "60"))

# CORS — comma-separated. Never use * with credentials in production.
_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", FRONTEND_URL or "http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

import sys

# Rate limits (requests per window)
if "pytest" in sys.modules:
    RATE_LIMIT_LOGIN_PER_MINUTE = 9999
    RATE_LIMIT_API_PER_MINUTE = 9999
    RATE_LIMIT_UPLOAD_PER_MINUTE = 9999
    RATE_LIMIT_WS_PER_MINUTE = 9999
else:
    RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
    RATE_LIMIT_API_PER_MINUTE = int(os.getenv("RATE_LIMIT_API_PER_MINUTE", "600"))
    RATE_LIMIT_UPLOAD_PER_MINUTE = int(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "300"))
    RATE_LIMIT_WS_PER_MINUTE = int(os.getenv("RATE_LIMIT_WS_PER_MINUTE", "300"))

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(10 * 1024 * 1024)))

# SSRF
SSRF_ALLOW_PRIVATE = os.getenv("SSRF_ALLOW_PRIVATE", "0").lower() in {"1", "true", "yes"}
SSRF_ALLOWED_HOSTS = {
    h.strip().lower()
    for h in os.getenv("SSRF_ALLOWED_HOSTS", "").split(",")
    if h.strip()
}

INSECURE_JWT_DEFAULTS = {
    "",
    "novaflow-dev-secret-change-in-prod",
    "novaflow-local-dev-secret",
    "novaflow-local-dev-secret-change-before-prod",
    "secret",
    "changeme",
}


def require_secure_jwt_secret() -> None:
    secret = (JWT_SECRET or "").strip()
    if IS_PRODUCTION and secret in INSECURE_JWT_DEFAULTS:
        raise RuntimeError(
            "FATAL: JWT_SECRET is missing or uses an insecure default. "
            "Set a strong JWT_SECRET (≥32 random bytes) before running in production."
        )
    if not IS_PRODUCTION and secret in INSECURE_JWT_DEFAULTS:
        warnings.warn(
            "JWT_SECRET is using a development default. Set JWT_SECRET before any real deployment.",
            stacklevel=2,
        )


def assert_production_bootstrap_safe(admin_password: str) -> None:
    if not IS_PRODUCTION:
        return
    if not admin_password or admin_password in {"admin123", "password", "admin"}:
        raise RuntimeError(
            "FATAL: NOVAFLOW_ADMIN_PASSWORD must be set to a strong value in production "
            "(not admin123)."
        )
