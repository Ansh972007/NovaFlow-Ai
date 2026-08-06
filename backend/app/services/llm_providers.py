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
        "chat_models": ["gpt-4o-mini", "gpt-4o", "gpt-4.5-preview", "o1-mini", "o3-mini"],
        "embedding_models": EMBEDDING_MODELS,
        "default_chat": OPENAI_MODEL,
        "default_embedding": OPENAI_EMBEDDING_MODEL,
        "supports_embeddings": True,
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "chat_models": [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.1-8b-instruct",
        ],
        "embedding_models": [
            "openai/text-embedding-3-small",
            "openai/text-embedding-ada-002",
        ],
        "default_chat": "openai/gpt-4o-mini",
        "default_embedding": "openai/text-embedding-3-small",
        "supports_embeddings": True,
    },
    "anthropic": {
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "chat_models": [
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
        ],
        "embedding_models": [],
        "default_chat": "claude-3-5-sonnet-latest",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "chat_models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "embedding_models": ["text-embedding-004"],
        "default_chat": "gemini-1.5-flash",
        "default_embedding": "text-embedding-004",
        "supports_embeddings": True,
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "chat_models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "embedding_models": [],
        "default_chat": "llama-3.3-70b-versatile",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "chat_models": ["deepseek-chat", "deepseek-reasoner"],
        "embedding_models": [],
        "default_chat": "deepseek-chat",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "together": {
        "label": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "chat_models": ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "embedding_models": ["togethercomputer/mxbai-embed-large-v1"],
        "default_chat": "meta-llama/Llama-3-70b-chat-hf",
        "default_embedding": "togethercomputer/mxbai-embed-large-v1",
        "supports_embeddings": True,
    },
    "mistral": {
        "label": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "chat_models": ["mistral-large-latest", "open-mixtral-8x22"],
        "embedding_models": ["mistral-embed"],
        "default_chat": "mistral-large-latest",
        "default_embedding": "mistral-embed",
        "supports_embeddings": True,
    },
    "cohere": {
        "label": "Cohere",
        "base_url": "https://api.cohere.ai/v1",
        "chat_models": ["command-r-plus", "command-r"],
        "embedding_models": ["embed-english-v3.0"],
        "default_chat": "command-r-plus",
        "default_embedding": "embed-english-v3.0",
        "supports_embeddings": True,
    },
    "fireworks": {
        "label": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "chat_models": ["accounts/fireworks/models/llama-v3-70b-instruct"],
        "embedding_models": ["nomic-ai/nomic-embed-text-v1.5"],
        "default_chat": "accounts/fireworks/models/llama-v3-70b-instruct",
        "default_embedding": "nomic-ai/nomic-embed-text-v1.5",
        "supports_embeddings": True,
    },
    "sambanova": {
        "label": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "chat_models": ["Meta-Llama-3.1-70B-Instruct", "Meta-Llama-3.1-405B-Instruct"],
        "embedding_models": [],
        "default_chat": "Meta-Llama-3.1-70B-Instruct",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "cerebras": {
        "label": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "chat_models": ["llama3.1-70b", "llama3.1-8b"],
        "embedding_models": [],
        "default_chat": "llama3.1-70b",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "xai": {
        "label": "xAI (Grok)",
        "base_url": "https://api.x.ai/v1",
        "chat_models": ["grok-2", "grok-2-vision"],
        "embedding_models": [],
        "default_chat": "grok-2",
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
    "vertex_ai": {
        "label": "Google Vertex AI",
        "base_url": "https://us-central1-aiplatform.googleapis.com/v1",
        "chat_models": ["gemini-1.5-pro", "gemini-1.5-flash"],
        "embedding_models": ["text-embedding-004"],
        "default_chat": "gemini-1.5-pro",
        "default_embedding": "text-embedding-004",
        "supports_embeddings": True,
    },
    "aws_bedrock": {
        "label": "AWS Bedrock (Proxy)",
        "base_url": "http://localhost:8000/v1",
        "chat_models": ["anthropic.claude-3-5-sonnet-20240620-v1:0"],
        "embedding_models": ["amazon.titan-embed-text-v1"],
        "default_chat": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "default_embedding": "amazon.titan-embed-text-v1",
        "supports_embeddings": True,
    },
    "cloudflare": {
        "label": "Cloudflare Workers AI",
        "base_url": "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/ai/v1",
        "chat_models": ["@cf/meta/llama-3-8b-instruct"],
        "embedding_models": ["@cf/baai/bge-large-en-v1.5"],
        "default_chat": "@cf/meta/llama-3-8b-instruct",
        "default_embedding": "@cf/baai/bge-large-en-v1.5",
        "supports_embeddings": True,
    },
    "ollama": {
        "label": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "chat_models": ["llama3", "mistral", "phi3", "deepseek-coder"],
        "embedding_models": ["nomic-embed-text"],
        "default_chat": "llama3",
        "default_embedding": "nomic-embed-text",
        "supports_embeddings": True,
    },
    "lm_studio": {
        "label": "LM Studio",
        "base_url": "http://localhost:1234/v1",
        "chat_models": ["meta-llama-3-8b-instruct"],
        "embedding_models": [],
        "default_chat": "meta-llama-3-8b-instruct",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "vllm": {
        "label": "vLLM",
        "base_url": "http://localhost:8000/v1",
        "chat_models": ["meta-llama/Meta-Llama-3-8B-Instruct"],
        "embedding_models": [],
        "default_chat": "meta-llama/Meta-Llama-3-8B-Instruct",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "localai": {
        "label": "LocalAI",
        "base_url": "http://localhost:8080/v1",
        "chat_models": ["gpt-4"],
        "embedding_models": ["text-embedding-ada-002"],
        "default_chat": "gpt-4",
        "default_embedding": "text-embedding-ada-002",
        "supports_embeddings": True,
    },
    "llamacpp": {
        "label": "llama.cpp",
        "base_url": "http://localhost:8080/v1",
        "chat_models": ["default"],
        "embedding_models": [],
        "default_chat": "default",
        "default_embedding": "",
        "supports_embeddings": False,
    },
    "custom": {
        "label": "Custom OpenAI-compatible",
        "base_url": "http://localhost:11434/v1",
        "chat_models": ["llama3", "mistral"],
        "embedding_models": ["text-embedding-3-small"],
        "default_chat": "llama3",
        "default_embedding": "text-embedding-3-small",
        "supports_embeddings": True,
    },
}


def openai_compat_headers(api_key: str, base_url: str = "") -> dict[str, str]:
    """Bearer headers; adds OpenRouter Referer/Title when needed."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "openrouter.ai" in (base_url or "").lower():
        from app.config import OPENROUTER_APP_TITLE, OPENROUTER_HTTP_REFERER

        headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
        headers["X-Title"] = OPENROUTER_APP_TITLE
    return headers


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
    # Fallback to environment variable
    if OPENAI_API_KEY:
        return OPENAI_API_KEY
    return ""


def get_active_config(db: Session | None = None, conversation_api_key: str | None = None, user_id: int | None = None) -> dict[str, str]:
    # STRICT SECURITY: User API keys are MANDATORY - no system fallback allowed
    # This is a production-grade security requirement
    
    # Priority 1: Use API key from conversation if provided
    if conversation_api_key:
        # Detect provider type from API key format
        ptype = "openrouter" if conversation_api_key.startswith("sk-or-") else "openai"
        meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
        
        return {
            "provider_id": "conversation",
            "provider_type": ptype,
            "provider_name": f"Conversation-provided ({ptype})",
            "api_key": conversation_api_key,
            "base_url": meta["base_url"].rstrip("/"),
            "model": meta["default_chat"],
            "embedding_model": meta.get("default_embedding") or OPENAI_EMBEDDING_MODEL,
        }
    
    # Priority 2: Use user-specific API key (MANDATORY for chat)
    if db is not None and user_id is not None:
        from app.services.user_management import UserApiKeyManager
        user_api_manager = UserApiKeyManager(db)
        user_api_key = user_api_manager.get_user_api_key(user_id)
        
        if user_api_key:
            user_config = user_api_manager.get_user_api_config(user_id)
            ptype = user_config.get("provider", "openrouter")
            meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
            
            return {
                "provider_id": f"user_{user_id}",
                "provider_type": ptype,
                "provider_name": f"User-specific ({ptype})",
                "api_key": user_api_key,
                "base_url": user_api_manager.get_base_url_for_user(user_id),
                "model": user_api_manager.get_model_for_user(user_id),
                "embedding_model": meta.get("default_embedding") or OPENAI_EMBEDDING_MODEL,
            }
        
    # Priority 2.5: Use Credential Vault API key if saved in workspace credentials
    if db is not None:
        try:
            from app.services.credential_vault import get_credential
            ws_id = getattr(db, "_workspace_id", 1) or 1
            vault_key = get_credential(db, ws_id, "llm", "openai", "api_key") or get_credential(db, ws_id, "llm", "openrouter", "api_key")
            if vault_key:
                ptype = "openrouter" if vault_key.startswith("sk-or-") else "openai"
                meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
                return {
                    "provider_id": "vault",
                    "provider_type": ptype,
                    "provider_name": f"Vault-provided ({ptype})",
                    "api_key": vault_key,
                    "base_url": meta["base_url"].rstrip("/"),
                    "model": meta["default_chat"],
                    "embedding_model": meta.get("default_embedding") or OPENAI_EMBEDDING_MODEL,
                }
        except Exception:
            pass

    # Priority 3: Fall back to system active provider or environment configuration
    if db is not None:
        row = get_active_provider_row(db)
        if row:
            ptype = (row.provider_type or "openai").lower()
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

    # Environment fallback (only if set by user or admin in environment)
    import os
    ptype = (os.getenv("OPENAI_PROVIDER_TYPE") or "openrouter").lower()
    meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openrouter"])
    env_key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    return {
        "provider_id": "",
        "provider_type": ptype,
        "provider_name": "Environment",
        "api_key": env_key,
        "base_url": (os.getenv("OPENAI_BASE_URL") or meta["base_url"]).rstrip("/"),
        "model": os.getenv("OPENAI_MODEL") or meta["default_chat"],
        "embedding_model": OPENAI_EMBEDDING_MODEL or meta.get("default_embedding") or "openai/text-embedding-3-small",
    }


def ensure_default_provider(db: Session) -> None:
    # Only set up default provider if user has explicitly configured one
    # Don't auto-create from environment variables - require user to upload their own key
    if db.query(LlmProvider).count() > 0:
        if not get_active_provider_row(db):
            first = db.query(LlmProvider).order_by(LlmProvider.id).first()
            if first:
                first.is_active = 1
                db.commit()
        return

    # Don't auto-create default provider - user must upload their own API key
    return


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


def verify_provider(db: Session, provider_id: int) -> dict:
    """Ping chat (and embeddings when supported) for a provider vault row."""
    import httpx

    row = db.get(LlmProvider, provider_id)
    if not row:
        raise ValueError("Provider not found")
    ptype = row.provider_type or "openai"
    meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
    api_key = resolve_api_key(row)
    if not api_key:
        raise ValueError("No API key configured for this provider")
    base_url = (row.base_url or meta["base_url"]).rstrip("/")
    model = row.chat_model or meta["default_chat"]
    headers = openai_compat_headers(api_key, base_url)
    result = {
        "ok": False,
        "provider_id": row.id,
        "provider_type": ptype,
        "chat_ok": False,
        "embedding_ok": None,
        "model": model,
        "detail": "",
    }
    with httpx.Client(timeout=45) as client:
        if ptype == "anthropic":
            url = f"{base_url}/v1/messages" if not base_url.endswith("/v1/messages") else base_url
            res = client.post(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 8,
                    "messages": [{"role": "user", "content": "Reply with OK"}],
                },
            )
        else:
            res = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with OK"}],
                    "max_tokens": 8,
                },
            )
        if res.status_code >= 400:
            result["detail"] = res.text[:240]
            return result
        result["chat_ok"] = True

        if meta.get("supports_embeddings"):
            emb_model = row.embedding_model or meta.get("default_embedding") or OPENAI_EMBEDDING_MODEL
            emb = client.post(
                f"{base_url}/embeddings",
                headers=headers,
                json={"model": emb_model, "input": ["NovaFlow connection test"]},
            )
            result["embedding_ok"] = emb.status_code < 400
            if emb.status_code >= 400:
                result["detail"] = f"chat ok; embeddings failed: {emb.text[:180]}"
            else:
                result["detail"] = "chat and embeddings OK"
        else:
            result["detail"] = "chat OK (embeddings not supported)"

    result["ok"] = bool(result["chat_ok"])
    return result


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
