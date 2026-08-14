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
_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
_origin_set = {"http://localhost:3000", "http://127.0.0.1:3000"}
if FRONTEND_URL:
    _origin_set.add(FRONTEND_URL.strip().rstrip("/"))
if _raw_origins:
    for o in _raw_origins.split(","):
        if o.strip():
            _origin_set.add(o.strip().rstrip("/"))
CORS_ALLOWED_ORIGINS = sorted(list(_origin_set))

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
# Chat chunked uploads — up to 2 GiB per file (async extract/index for large files).
MAX_CHAT_UPLOAD_BYTES = int(os.getenv("MAX_CHAT_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
# Sync text extract on upload complete only below this size; larger files extract in background.
SYNC_EXTRACT_MAX_BYTES = int(os.getenv("SYNC_EXTRACT_MAX_BYTES", str(32 * 1024 * 1024)))
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
    "novaflow-dev-jwt-change-me-in-production",
    "novaflow-test-secret",
    "secret",
    "changeme",
    "change-me",
    "change_me",
}

WEAK_ADMIN_PASSWORDS = {
    "",
    "admin",
    "admin123",
    "password",
    "password123",
    "novaflow",
    "demo123",
    "changeme",
}


def require_secure_jwt_secret() -> None:
    secret = (JWT_SECRET or "").strip()
    if IS_PRODUCTION and (secret in INSECURE_JWT_DEFAULTS or len(secret) < 32):
        raise RuntimeError(
            "FATAL: JWT_SECRET is missing, too short, or uses an insecure default. "
            "Set a strong JWT_SECRET (≥32 random bytes) before running in production."
        )
    if not IS_PRODUCTION and secret in INSECURE_JWT_DEFAULTS:
        warnings.warn(
            "JWT_SECRET is using a development default. Set JWT_SECRET before any real deployment.",
            stacklevel=2,
        )


def is_strong_bootstrap_password(admin_password: str) -> bool:
    pwd = (admin_password or "").strip()
    if not pwd or pwd.lower() in WEAK_ADMIN_PASSWORDS:
        return False
    if len(pwd) < 16:
        return False
    return True


def assert_production_bootstrap_safe(admin_password: str) -> None:
    if not IS_PRODUCTION:
        return
    if not is_strong_bootstrap_password(admin_password):
        raise RuntimeError(
            "FATAL: NOVAFLOW_ADMIN_PASSWORD must be set to a strong value in production "
            "(≥16 characters, not a known default like admin123)."
        )


def assert_first_admin_password(admin_password: str) -> None:
    """Required whenever the users table is empty (any environment)."""
    if not is_strong_bootstrap_password(admin_password):
        raise RuntimeError(
            "FATAL: NOVAFLOW_ADMIN_PASSWORD must be set (≥16 characters, not a known "
            "default) before creating the first admin user."
        )
