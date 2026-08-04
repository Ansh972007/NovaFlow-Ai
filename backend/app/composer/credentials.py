from app.crypto import encrypt_secret, decrypt_secret

def secure_vault_save(plain_secret: str) -> str:
    """Encrypt a secret string for database storage."""
    return encrypt_secret(plain_secret)


def secure_vault_read(encrypted_secret: str) -> str:
    """Decrypt a secret string safely."""
    return decrypt_secret(encrypted_secret)


def mask_credential(plain_secret: str) -> str:
    """Returns a safe, masked representation of a credential for UI listings."""
    if not plain_secret:
        return ""
    if len(plain_secret) <= 8:
        return "****"
    return f"{plain_secret[:4]}...{plain_secret[-4:]}"
