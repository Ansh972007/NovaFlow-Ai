"""Platform mail + SMTP secrecy tests."""

from app.services.platform_mail import platform_mail_ready, platform_smtp_config, send_platform_email_sync
from app.services.workspace_integrations import _mask_secret, integrations_dict
from app.database import SessionLocal


def test_platform_smtp_strips_app_password_spaces():
    cfg = platform_smtp_config()
    assert cfg["host"] == "smtp.gmail.com"
    assert cfg["user"] == "novaflow85@gmail.com"
    assert " " not in cfg["password"]
    assert len(cfg["password"]) >= 16
    assert platform_mail_ready() is True


def test_mask_secret_never_leaks_chars():
    assert _mask_secret("whlijwomrrluspph") == "••••••••"
    assert "whli" not in _mask_secret("whli jwom rrlu spph")
    assert "spph" not in _mask_secret("whlijwomrrluspph")


def test_integrations_dict_hides_smtp_password():
    db = SessionLocal()
    try:
        data = integrations_dict(db, 1)
        blob = str(data)
        assert "whli" not in blob
        assert "rrlu" not in blob
        assert "smtp_password" not in (data.get("email") or {}) or "smtp_password_masked" in data["email"]
        assert data["email"].get("smtp_password_configured") is True or data["email"].get("configured") is True
        # raw password key must not exist
        assert "smtp_password" not in data.get("email", {})
        assert "password" not in data.get("email", {})
    finally:
        db.close()


def test_send_platform_email_rejects_empty_recipient():
    result = send_platform_email_sync("", "subj", "body")
    assert result.get("ok") is False
