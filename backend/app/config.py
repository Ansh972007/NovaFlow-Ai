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

EMBEDDING_MODELS = ["text-embedding-3-small", "text-embedding-ada-002"]
