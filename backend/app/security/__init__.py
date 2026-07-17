"""
NovaFlow Enterprise Security Foundation.

All authentication, authorization, transport hardening, SSRF controls,
audit logging, and rate limiting flow through this package so future
features inherit the same guarantees without duplicating logic.
"""

from app.security.passwords import (
    hash_password,
    verify_password,
    needs_rehash,
    validate_password_policy,
    PasswordPolicyError,
)
from app.security.tokens import (
    issue_token_pair,
    decode_access_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_sessions,
    TokenError,
)
from app.security.rbac import (
    ROLE_RANK,
    normalize_role,
    has_min_role,
    Permission,
    role_has_permission,
)
from app.security.ssrf import assert_safe_url, SafeUrlError
from app.security.audit import audit_log
from app.security.rate_limit import RateLimiter, rate_limiter

__all__ = [
    "hash_password",
    "verify_password",
    "needs_rehash",
    "validate_password_policy",
    "PasswordPolicyError",
    "issue_token_pair",
    "decode_access_token",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "revoke_all_user_sessions",
    "TokenError",
    "ROLE_RANK",
    "normalize_role",
    "has_min_role",
    "Permission",
    "role_has_permission",
    "assert_safe_url",
    "SafeUrlError",
    "audit_log",
    "RateLimiter",
    "rate_limiter",
]
