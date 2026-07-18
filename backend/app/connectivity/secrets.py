"""ECP secret management — encryption, rotation, scoped access."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crypto import decrypt_secret, encrypt_secret
from app.database import ConnectorCredential


def encrypt_credential(plain: str) -> str:
    return encrypt_secret(plain or "")


def decrypt_credential(enc: str) -> str:
    return decrypt_secret(enc or "")


def rotate_credential(
    db: Session,
    cred: ConnectorCredential,
    *,
    new_secret: str,
) -> ConnectorCredential:
    cred.secret_enc = encrypt_credential(new_secret)
    cred.version_no = (cred.version_no or 1) + 1
    cred.rotated_at = datetime.utcnow()
    db.commit()
    db.refresh(cred)
    return cred


def mask_secret(value: str, *, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def credential_dict(cred: ConnectorCredential, *, include_secret: bool = False) -> dict[str, Any]:
    d = {
        "id": cred.id,
        "connection_id": cred.connection_id,
        "credential_type": cred.credential_type,
        "version_no": cred.version_no,
        "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
        "rotated_at": cred.rotated_at.isoformat() if cred.rotated_at else None,
    }
    if include_secret:
        d["secret"] = mask_secret(decrypt_credential(cred.secret_enc))
    return d
