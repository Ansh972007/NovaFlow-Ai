from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import (
    EMBEDDING_MODELS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_MODEL,
)
from app.crypto import decrypt_secret, encrypt_secret
from app.database import LlmProvider

PROVIDER_TYPES: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "chat_models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-3.5-turbo"],
        "embedding_models": EMBEDDING_MODELS,
        "default_chat": OPENAI_MODEL,
        "default_embedding": OPENAI_EMBEDDING_MODEL,
        "supports_embeddings": True,
    },
    "anthropic": {
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "chat_models": [
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
        ],
        "embedding_models": [],
        "default_chat": "claude-sonnet-4-20250514",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "azure_openai": {
        "label": "Azure OpenAI",
        "base_url": "https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT",
        "chat_models": ["gpt-4o-mini", "gpt-4o"],
        "embedding_models": EMBEDDING_MODELS,
        "default_chat": "gpt-4o-mini",
        "default_embedding": "text-embedding-3-small",
        "supports_embeddings": True,
    },
    "custom": {
        "label": "OpenAI-compatible",
        "base_url": "http://localhost:11434/v1",
        "chat_models": ["llama3", "mistral", "qwen2.5"],
        "embedding_models": ["text-embedding-3-small"],
        "default_chat": "llama3",
        "default_embedding": "text-embedding-3-small",
        "supports_embeddings": True,
    },
}


def _key_hint(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "••••"
    return f"••••{api_key[-4:]}"


def provider_dict(row: LlmProvider, include_hint: bool = True) -> dict:
    plain_key = decrypt_secret(row.api_key_enc or "")
    return {
        "id": row.id,
        "name": row.name,
        "provider_type": row.provider_type,
        "base_url": row.base_url or "",
        "chat_model": row.chat_model or "",
        "embedding_model": row.embedding_model or "",
        "is_active": bool(row.is_active),
        "api_key_configured": bool(plain_key or (row.is_active and not row.api_key_enc and OPENAI_API_KEY)),
        "api_key_hint": _key_hint(plain_key) if include_hint else "",
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "update_time": row.update_time.isoformat() if row.update_time else None,
    }


def list_provider_types() -> list[dict]:
    return [
        {
            "id": key,
            "label": meta["label"],
            "base_url": meta["base_url"],
            "chat_models": meta["chat_models"],
            "embedding_models": meta["embedding_models"],
            "default_chat": meta["default_chat"],
            "default_embedding": meta["default_embedding"],
            "supports_embeddings": meta["supports_embeddings"],
        }
        for key, meta in PROVIDER_TYPES.items()
    ]


def list_providers(db: Session) -> list[dict]:
    rows = db.query(LlmProvider).order_by(LlmProvider.id).all()
    return [provider_dict(r) for r in rows]


def get_active_provider_row(db: Session) -> LlmProvider | None:
    return db.query(LlmProvider).filter(LlmProvider.is_active == 1).order_by(LlmProvider.id).first()


def resolve_api_key(row: LlmProvider | None) -> str:
    if row and row.api_key_enc:
        return decrypt_secret(row.api_key_enc)
    return OPENAI_API_KEY


def get_active_config(db: Session | None = None) -> dict[str, str]:
    row = None
    if db is not None:
        row = get_active_provider_row(db)

    if row:
        ptype = row.provider_type or "openai"
        meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
        return {
            "provider_id": str(row.id),
            "provider_type": ptype,
            "provider_name": row.name,
            "api_key": resolve_api_key(row),
            "base_url": (row.base_url or meta["base_url"]).rstrip("/"),
            "model": row.chat_model or meta["default_chat"],
            "embedding_model": row.embedding_model or meta.get("default_embedding") or OPENAI_EMBEDDING_MODEL,
        }

    return {
        "provider_id": "",
        "provider_type": "openai",
        "provider_name": "Environment",
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_BASE_URL.rstrip("/"),
        "model": OPENAI_MODEL,
        "embedding_model": OPENAI_EMBEDDING_MODEL,
    }


def ensure_default_provider(db: Session) -> None:
    if db.query(LlmProvider).count() > 0:
        if not get_active_provider_row(db):
            first = db.query(LlmProvider).order_by(LlmProvider.id).first()
            if first:
                first.is_active = 1
                db.commit()
        return

    if not OPENAI_API_KEY:
        return

    row = LlmProvider(
        name="OpenAI (env)",
        provider_type="openai",
        base_url=OPENAI_BASE_URL.rstrip("/"),
        api_key_enc="",
        chat_model=OPENAI_MODEL,
        embedding_model=OPENAI_EMBEDDING_MODEL,
        is_active=1,
    )
    db.add(row)
    db.commit()


def create_provider(db: Session, data: dict) -> dict:
    ptype = (data.get("provider_type") or "openai").strip().lower()
    if ptype not in PROVIDER_TYPES:
        raise ValueError("Invalid provider type")
    meta = PROVIDER_TYPES[ptype]
    name = (data.get("name") or meta["label"]).strip()[:120]
    if not name:
        raise ValueError("Provider name required")

    count_before = db.query(LlmProvider).count()
    api_key = (data.get("api_key") or "").strip()
    row = LlmProvider(
        name=name,
        provider_type=ptype,
        base_url=(data.get("base_url") or meta["base_url"]).strip().rstrip("/"),
        api_key_enc=encrypt_secret(api_key) if api_key else "",
        chat_model=(data.get("chat_model") or meta["default_chat"]).strip(),
        embedding_model=(data.get("embedding_model") or meta.get("default_embedding") or "").strip(),
        is_active=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if data.get("activate") or count_before == 0:
        activate_provider(db, row.id)

    return provider_dict(row)


def update_provider(db: Session, provider_id: int, data: dict) -> dict:
    row = db.get(LlmProvider, provider_id)
    if not row:
        raise ValueError("Provider not found")

    if "name" in data and data["name"]:
        row.name = str(data["name"]).strip()[:120]
    if "base_url" in data and data["base_url"]:
        row.base_url = str(data["base_url"]).strip().rstrip("/")
    if "chat_model" in data and data["chat_model"]:
        row.chat_model = str(data["chat_model"]).strip()
    if "embedding_model" in data and data["embedding_model"] is not None:
        row.embedding_model = str(data["embedding_model"]).strip()
    if "api_key" in data:
        key = str(data["api_key"] or "").strip()
        if key:
            row.api_key_enc = encrypt_secret(key)
        elif data["api_key"] is None:
            row.api_key_enc = ""

    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return provider_dict(row)


def delete_provider(db: Session, provider_id: int) -> None:
    row = db.get(LlmProvider, provider_id)
    if not row:
        raise ValueError("Provider not found")
    was_active = row.is_active
    db.delete(row)
    db.commit()
    if was_active:
        nxt = db.query(LlmProvider).order_by(LlmProvider.id).first()
        if nxt:
            nxt.is_active = 1
            db.commit()


def activate_provider(db: Session, provider_id: int) -> dict:
    row = db.get(LlmProvider, provider_id)
    if not row:
        raise ValueError("Provider not found")
    db.query(LlmProvider).update({LlmProvider.is_active: 0})
    row.is_active = 1
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return provider_dict(row)


def settings_summary(db: Session) -> dict:
    cfg = get_active_config(db)
    active = get_active_provider_row(db)
    ptype = active.provider_type if active else "openai"
    meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
    return {
        "active_provider_id": active.id if active else None,
        "provider_type": ptype,
        "provider_name": active.name if active else "Environment",
        "chat_model": cfg["model"],
        "embedding_model": cfg["embedding_model"],
        "openai_base_url": cfg["base_url"],
        "api_key_configured": bool(cfg["api_key"]),
        "embedding_models": meta.get("embedding_models") or EMBEDDING_MODELS,
        "chat_models": meta.get("chat_models") or [],
        "providers": list_providers(db),
        "provider_types": list_provider_types(),
    }
