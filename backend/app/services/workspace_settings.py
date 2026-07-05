from datetime import datetime

from sqlalchemy.orm import Session

from app.config import EMBEDDING_MODELS, OPENAI_MODEL
from app.database import WorkspaceSetting
from app.services.llm_providers import (
    ensure_default_provider,
    get_active_config,
    settings_summary,
    update_provider,
    get_active_provider_row,
)


def load_settings(db: Session) -> None:
    ensure_default_provider(db)


def get_chat_config(db: Session | None = None) -> dict[str, str]:
    if db is None:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            return get_active_config(db)
        finally:
            db.close()
    return get_active_config(db)


def get_embedding_model(db: Session | None = None) -> str:
    return get_chat_config(db)["embedding_model"]


def settings_dict(db: Session) -> dict:
    load_settings(db)
    return settings_summary(db)


def update_settings(db: Session, data: dict) -> dict:
    """Update the active provider's models (legacy settings endpoint)."""
    load_settings(db)
    active = get_active_provider_row(db)
    if active:
        patch = {}
        if "chat_model" in data and data["chat_model"]:
            patch["chat_model"] = data["chat_model"]
        if "embedding_model" in data and data["embedding_model"]:
            model = str(data["embedding_model"]).strip()
            if model in EMBEDDING_MODELS or not EMBEDDING_MODELS:
                patch["embedding_model"] = model
        if "openai_base_url" in data and data["openai_base_url"]:
            patch["base_url"] = data["openai_base_url"]
        if patch:
            update_provider(db, active.id, patch)
    else:
        row = db.query(WorkspaceSetting).filter(WorkspaceSetting.id == 1).first()
        if not row:
            row = WorkspaceSetting(id=1)
            db.add(row)
        if "chat_model" in data and data["chat_model"]:
            row.chat_model = str(data["chat_model"]).strip()
        if "embedding_model" in data and data["embedding_model"]:
            row.embedding_model = str(data["embedding_model"]).strip()
        if "openai_base_url" in data and data["openai_base_url"]:
            row.openai_base_url = str(data["openai_base_url"]).strip().rstrip("/")
        row.updated_at = datetime.utcnow()
        db.commit()

    return settings_summary(db)
