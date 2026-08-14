import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.getenv("PORT") or os.getenv("NOVAFLOW_PORT", "3001"))
NOVAFLOW_ENV = os.getenv("NOVAFLOW_ENV", "development")

_raw_db_url = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'novaflow.db').as_posix()}",
)
# Normalize Supabase / Heroku legacy postgres:// schema to standard postgresql://
if _raw_db_url.startswith("postgres://"):
    DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = _raw_db_url

REDIS_URL = os.getenv("REDIS_URL", "")
_raw_jwt = (os.getenv("JWT_SECRET") or "").strip()
if _raw_jwt and len(_raw_jwt) >= 32 and _raw_jwt != "novaflow-dev-secret-change-in-prod":
    JWT_SECRET = _raw_jwt
elif NOVAFLOW_ENV in ("production", "prod"):
    import secrets

    JWT_SECRET = _raw_jwt if len(_raw_jwt) >= 32 else secrets.token_hex(32)
else:
    JWT_SECRET = _raw_jwt or "novaflow-dev-secret-change-in-prod"

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

ADMIN_USER = os.getenv("NOVAFLOW_ADMIN_USER", "admin")
_dev_default_admin_password = "NovaFlowLocalDevAdmin1"
_raw_admin_password = (os.getenv("NOVAFLOW_ADMIN_PASSWORD") or "").strip()
if _raw_admin_password:
    ADMIN_PASSWORD = _raw_admin_password
else:
    ADMIN_PASSWORD = _dev_default_admin_password

DEMO_SEED = os.getenv("NOVAFLOW_DEMO_SEED", "").lower() in {"1", "true", "yes"}
ALLOW_PUBLIC_REGISTER = os.getenv("ALLOW_PUBLIC_REGISTER", "0").lower() in {"1", "true", "yes"}
# Password login disabled by default — use Google (Gmail) OAuth in production.
ALLOW_PASSWORD_LOGIN = os.getenv("ALLOW_PASSWORD_LOGIN", "0").lower() in {"1", "true", "yes"}
# When enabled, only @gmail.com addresses may authenticate (OAuth or password).
GMAIL_ONLY_AUTH = os.getenv("GMAIL_ONLY_AUTH", "1").lower() in {"1", "true", "yes"}

EMBEDDING_MODELS = [
    "text-embedding-3-small",
    "text-embedding-ada-002",
    "openai/text-embedding-3-small",
    "openai/text-embedding-ada-002",
]
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
MILVUS_URI = os.getenv("MILVUS_URI", "")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Public HTTPS base for Telegram/Slack webhooks & Render external domain
PUBLIC_BASE_URL = (
    os.getenv("NOVAFLOW_PUBLIC_BASE_URL")
    or os.getenv("PUBLIC_BASE_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or ""
).strip().rstrip("/")

OAUTH_REDIRECT_BASE = (
    os.getenv("OAUTH_REDIRECT_BASE")
    or PUBLIC_BASE_URL
    or f"http://localhost:{PORT}"
).rstrip("/")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", FRONTEND_URL)
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "NovaFlow AI")

LDAP_URL = os.getenv("LDAP_URL", "")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "")
LDAP_USER_FILTER = os.getenv("LDAP_USER_FILTER", "(uid={username})")
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")

SAML_IDP_SSO_URL = os.getenv("SAML_IDP_SSO_URL", "")
SAML_IDP_ENTITY_ID = os.getenv("SAML_IDP_ENTITY_ID", "")
SAML_SP_ENTITY_ID = os.getenv("SAML_SP_ENTITY_ID", "novaflow-ai")
SAML_IDP_CERT = os.getenv("SAML_IDP_CERT", "")

# Platform transactional mail (password reset, team invites). Server-side only —
# never returned to the browser. Override via env in production if needed.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "novaflow85@gmail.com")
# Gmail app password — spaces optional in env; stripped at send time.
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "whli jwom rrlu spph")
SMTP_FROM = os.getenv("SMTP_FROM", "novaflow85@gmail.com")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
