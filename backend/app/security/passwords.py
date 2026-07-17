"""Argon2id password hashing with pepper, legacy MD5 migration, and policy."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Optional

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHash, VerifyMismatchError

# Tunable via env — defaults match OWASP Argon2id recommendations for interactive logins.
_TIME_COST = int(os.getenv("PASSWORD_ARGON2_TIME_COST", "3"))
_MEMORY_COST = int(os.getenv("PASSWORD_ARGON2_MEMORY_COST", "65536"))  # KiB
_PARALLELISM = int(os.getenv("PASSWORD_ARGON2_PARALLELISM", "4"))
_HASH_LEN = int(os.getenv("PASSWORD_ARGON2_HASH_LEN", "32"))
_SALT_LEN = int(os.getenv("PASSWORD_ARGON2_SALT_LEN", "16"))

# Optional application-wide pepper (never store beside hashes in DB).
PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER", "")

# Policy: strong defaults for production; override via env for constrained demos.
_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
_REQUIRE_UPPER = os.getenv("PASSWORD_REQUIRE_UPPER", "0").lower() in {"1", "true", "yes"}
_REQUIRE_LOWER = os.getenv("PASSWORD_REQUIRE_LOWER", "0").lower() in {"1", "true", "yes"}
_REQUIRE_DIGIT = os.getenv("PASSWORD_REQUIRE_DIGIT", "0").lower() in {"1", "true", "yes"}
_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "0").lower() in {"1", "true", "yes"}

_ph = PasswordHasher(
    time_cost=_TIME_COST,
    memory_cost=_MEMORY_COST,
    parallelism=_PARALLELISM,
    hash_len=_HASH_LEN,
    salt_len=_SALT_LEN,
    type=Type.ID,
)


class PasswordPolicyError(ValueError):
    pass


def _pepper(plain: str) -> str:
    if not PASSWORD_PEPPER:
        return plain
    return hmac.new(PASSWORD_PEPPER.encode("utf-8"), plain.encode("utf-8"), hashlib.sha256).hexdigest() + ":" + plain


def hash_password(plain: str) -> str:
    return _ph.hash(_pepper(plain))


def _is_legacy_md5(stored: str) -> bool:
    return bool(stored) and len(stored) == 32 and re.fullmatch(r"[0-9a-f]{32}", stored or "") is not None


def _legacy_md5(plain: str) -> str:
    return hashlib.md5(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, stored: str) -> bool:
    if not plain or not stored:
        return False
    if _is_legacy_md5(stored):
        return hmac.compare_digest(_legacy_md5(plain), stored)
    try:
        return _ph.verify(stored, _pepper(plain))
    except (VerifyMismatchError, InvalidHash):
        return False


def needs_rehash(stored: str) -> bool:
    if not stored:
        return True
    if _is_legacy_md5(stored):
        return True
    try:
        return _ph.check_needs_rehash(stored)
    except Exception:
        return True


def validate_password_policy(plain: str) -> None:
    if plain is None:
        raise PasswordPolicyError("Password is required")
    pwd = plain.strip()
    if len(pwd) < _MIN_LENGTH:
        raise PasswordPolicyError(f"Password must be at least {_MIN_LENGTH} characters")
    if _REQUIRE_UPPER and not re.search(r"[A-Z]", pwd):
        raise PasswordPolicyError("Password must include an uppercase letter")
    if _REQUIRE_LOWER and not re.search(r"[a-z]", pwd):
        raise PasswordPolicyError("Password must include a lowercase letter")
    if _REQUIRE_DIGIT and not re.search(r"\d", pwd):
        raise PasswordPolicyError("Password must include a digit")
    if _REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", pwd):
        raise PasswordPolicyError("Password must include a special character")
    # Block the well-known bootstrap default in user-chosen passwords.
    if pwd.lower() in {"admin123", "password", "password123", "novaflow", "demo123"}:
        raise PasswordPolicyError("Password is too common")
