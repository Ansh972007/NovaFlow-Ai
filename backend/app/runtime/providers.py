"""Model provider registry — hot-swappable, OpenAI-compatible abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

# Extend catalog with explicit entries for routing docs; implementation delegates to llm_providers.
PROVIDER_ALIASES: dict[str, str] = {
    "google": "openrouter",
    "gemini": "openrouter",
    "google_gemini": "openrouter",
    "deepseek": "openrouter",
    "mistral": "openrouter",
    "qwen": "openrouter",
    "ollama": "custom",
}


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: int | None
    provider_type: str
    provider_name: str
    api_key: str
    base_url: str
    model: str
    embedding_model: str

    def to_dict(self) -> dict[str, str]:
        return {
            "provider_id": str(self.provider_id or ""),
            "provider_type": self.provider_type,
            "provider_name": self.provider_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "embedding_model": self.embedding_model,
        }


def resolve_provider(db: Session | None) -> ProviderConfig:
    from app.services.llm_providers import get_active_config

    raw = get_active_config(db)
    ptype = (raw.get("provider_type") or "openai").lower()
    ptype = PROVIDER_ALIASES.get(ptype, ptype)
    pid = raw.get("provider_id")
    return ProviderConfig(
        provider_id=int(pid) if pid else None,
        provider_type=ptype,
        provider_name=raw.get("provider_name") or ptype,
        api_key=raw.get("api_key") or "",
        base_url=raw.get("base_url") or "",
        model=raw.get("model") or "",
        embedding_model=raw.get("embedding_model") or "",
    )


def list_supported_providers() -> list[dict[str, Any]]:
    from app.services.llm_providers import PROVIDER_TYPES, list_provider_types

    types = list_provider_types()
    extras = [
        {"id": "ollama", "label": "Ollama (local)", "via": "custom"},
        {"id": "google_gemini", "label": "Google Gemini", "via": "openrouter"},
        {"id": "deepseek", "label": "DeepSeek", "via": "openrouter"},
        {"id": "mistral", "label": "Mistral", "via": "openrouter"},
        {"id": "qwen", "label": "Qwen", "via": "openrouter"},
    ]
    return types + extras
