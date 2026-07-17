"""Crypto facade — RSA transport + Fernet secrets + JWT helpers.

Password hashing and session tokens live in app.security.*; this module
keeps stable import paths used across the codebase.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple

import rsa
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.config import DATA_DIR, JWT_EXPIRE_HOURS, JWT_SECRET
from app.security.config import JWT_ALGORITHM, JWT_ISSUER
from app.security.passwords import hash_password, verify_password  # noqa: F401
from app.security.tokens import decode_access_token, issue_access_token

RSA_KEY_DIR = DATA_DIR / "keys"
_keys: Optional[Tuple[rsa.PublicKey, rsa.PrivateKey]] = None


def md5_hash(text: str) -> str:
    """Legacy helper retained for tests / migration detection only. Do not store new passwords with this."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_rsa_keys() -> Tuple[rsa.PublicKey, rsa.PrivateKey]:
    """2048-bit RSA keys persisted under DATA_DIR/keys for stable password transport."""
    global _keys
    if _keys is not None:
        return _keys

    RSA_KEY_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = RSA_KEY_DIR / "transport_private.pem"
    pub_path = RSA_KEY_DIR / "transport_public.pem"

    if priv_path.exists() and pub_path.exists():
        priv = rsa.PrivateKey.load_pkcs1(priv_path.read_bytes())
        pub = rsa.PublicKey.load_pkcs1(pub_path.read_bytes())
        _keys = (pub, priv)
        return _keys

    pub, priv = rsa.newkeys(2048)
    priv_path.write_bytes(priv.save_pkcs1())
    pub_path.write_bytes(pub.save_pkcs1())
    try:
        priv_path.chmod(0o600)
    except Exception:
        pass
    _keys = (pub, priv)
    return _keys


def get_public_key_pem() -> str:
    pub, _ = get_rsa_keys()
    return pub.save_pkcs1().decode("utf-8")


def decrypt_password_plain(encrypted_b64: str) -> str:
    _, priv = get_rsa_keys()
    return rsa.decrypt(base64.b64decode(encrypted_b64), priv).decode("utf-8")


def decrypt_password(encrypted_b64: str) -> str:
    """Decrypt RSA transport ciphertext and return Argon2id hash for storage."""
    return hash_password(decrypt_password_plain(encrypted_b64))


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(JWT_SECRET.encode()).digest())
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(enc: str) -> str:
    if not enc:
        return ""
    try:
        return _fernet().decrypt(enc.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def create_token(user_id: int, user_name: str, *, session_id: str = "", role: str = "editor") -> str:
    """Issue a short-lived access token. Prefer issue_token_pair() for full sessions."""
    if session_id:
        return issue_access_token(user_id, user_name, session_id=session_id, role=role)
    # Legacy path (OAuth interim) — still short-lived, no session binding
    from datetime import datetime, timedelta

    expire = datetime.utcnow() + timedelta(minutes=max(15, int(JWT_EXPIRE_HOURS * 60) if JWT_EXPIRE_HOURS < 1 else 15))
    # Cap legacy tokens at 15 minutes of access; refresh flow owns long sessions.
    expire = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode(
        {
            "sub": str(user_id),
            "user_name": user_name,
            "role": role,
            "typ": "access",
            "iss": JWT_ISSUER,
            "exp": expire,
            "iat": datetime.utcnow(),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode access token. Accepts new issuer-bound tokens and legacy tokens without iss."""
    payload = decode_access_token(token)
    if payload:
        return payload
    # Legacy tokens minted before issuer enforcement
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True, "verify_iss": False},
        )
    except JWTError:
        return None
