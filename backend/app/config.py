import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.getenv("NOVAFLOW_PORT", "3001"))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'novaflow.db').as_posix()}",
)
REDIS_URL = os.getenv("REDIS_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "novaflow-dev-secret-change-in-prod")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

ADMIN_USER = os.getenv("NOVAFLOW_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("NOVAFLOW_ADMIN_PASSWORD", "admin123")

DEMO_SEED = os.getenv("NOVAFLOW_DEMO_SEED", "").lower() in {"1", "true", "yes"}

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
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", f"http://localhost:{PORT}")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
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

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
