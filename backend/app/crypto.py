import hashlib
from base64 import b64decode
from datetime import datetime, timedelta
from typing import Optional, Tuple

import rsa
from jose import JWTError, jwt

from app.config import JWT_EXPIRE_HOURS, JWT_SECRET

RSA_KEY = "novaflow:rsa_keys"
_keys: Optional[Tuple[rsa.PublicKey, rsa.PrivateKey]] = None


def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_rsa_keys() -> Tuple[rsa.PublicKey, rsa.PrivateKey]:
    global _keys
    if _keys is None:
        _keys = rsa.newkeys(512)
    return _keys


def get_public_key_pem() -> str:
    pub, _ = get_rsa_keys()
    return pub.save_pkcs1().decode("utf-8")


def decrypt_password(encrypted_b64: str) -> str:
    return md5_hash(decrypt_password_plain(encrypted_b64))


def decrypt_password_plain(encrypted_b64: str) -> str:
    _, priv = get_rsa_keys()
    return rsa.decrypt(b64decode(encrypted_b64), priv).decode("utf-8")


def create_token(user_id: int, user_name: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "user_name": user_name, "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        return None
