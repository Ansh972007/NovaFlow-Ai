from datetime import datetime

from sqlalchemy.orm import Session

from app.config import (
    EMBEDDING_MODELS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_MODEL,
)
from app.database import WorkspaceSetting

_runtime = {
    "chat_model": OPENAI_MODEL,
    "embedding_model": OPENAI_EMBEDDING_MODEL,
    "openai_base_url": OPENAI_BASE_URL,
}


def load_settings(db: Session) -> None:
    global _runtime
    row = db.query(WorkspaceSetting).filter(WorkspaceSetting.id == 1).first()
    if not row:
        _runtime = {
            "chat_model": OPENAI_MODEL,
            "embedding_model": OPENAI_EMBEDDING_MODEL,
            "openai_base_url": OPENAI_BASE_URL,
        }
        return
    _runtime = {
        "chat_model": row.chat_model or OPENAI_MODEL,
        "embedding_model": row.embedding_model or OPENAI_EMBEDDING_MODEL,
        "openai_base_url": row.openai_base_url or OPENAI_BASE_URL,
    }


def get_chat_config() -> dict[str, str]:
    return {
        "api_key": OPENAI_API_KEY,
        "base_url": _runtime["openai_base_url"].rstrip("/"),
        "model": _runtime["chat_model"],
    }


def get_embedding_model() -> str:
    return _runtime["embedding_model"]


def settings_dict(db: Session) -> dict:
    load_settings(db)
    return {
        "chat_model": _runtime["chat_model"],
        "embedding_model": _runtime["embedding_model"],
        "openai_base_url": _runtime["openai_base_url"],
        "api_key_configured": bool(OPENAI_API_KEY),
        "embedding_models": EMBEDDING_MODELS,
        "chat_models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-3.5-turbo",
        ],
    }


def update_settings(db: Session, data: dict) -> dict:
    row = db.query(WorkspaceSetting).filter(WorkspaceSetting.id == 1).first()
    if not row:
        row = WorkspaceSetting(id=1)
        db.add(row)

    if "chat_model" in data and data["chat_model"]:
        row.chat_model = str(data["chat_model"]).strip()
    if "embedding_model" in data and data["embedding_model"]:
        model = str(data["embedding_model"]).strip()
        if model in EMBEDDING_MODELS:
            row.embedding_model = model
    if "openai_base_url" in data and data["openai_base_url"]:
        row.openai_base_url = str(data["openai_base_url"]).strip().rstrip("/")

    row.updated_at = datetime.utcnow()
    db.commit()
    load_settings(db)
    return settings_dict(db)
