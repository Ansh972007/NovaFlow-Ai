"""Unified LLM config resolution for chat planning (multi-provider / multi-model)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.llm_providers import PROVIDER_TYPES, get_active_config, list_providers


def _label_for_source(name: str, model: str) -> str:
    return f"{name} · {model}" if model else name


def list_llm_alternatives(db: Session, workspace_id: int, user_id: int, aios: dict[str, Any]) -> list[dict[str, Any]]:
    alts: list[dict[str, Any]] = []
    seen: set[str] = set()

    override = aios.get("planning_override") or {}
    if override.get("provider_id"):
        pid = str(override["provider_id"])
        alts.append(
            {
                "id": pid,
                "label": _label_for_source(override.get("provider_name") or "Chat override", override.get("model") or ""),
                "model": override.get("model"),
                "source": "override",
            }
        )
        seen.add(pid)

    if aios.get("conversation_api_key"):
        alts.append({"id": "conversation", "label": "Pasted in this chat", "model": None, "source": "conversation"})

    from app.services.user_management import UserApiKeyManager

    mgr = UserApiKeyManager(db)
    cfg = mgr.get_user_api_config(user_id)
    if cfg.get("has_api_key"):
        pid = f"user_{user_id}"
        alts.append(
            {
                "id": pid,
                "label": _label_for_source(f"Your {cfg.get('provider') or 'API'} key", cfg.get("model") or ""),
                "model": cfg.get("model"),
                "source": "user",
            }
        )
        seen.add(pid)

    try:
        from app.services.credential_vault import list_entries

        for row in list_entries(db, workspace_id, category="llm"):
            pid = f"vault_{row.id}"
            if pid in seen:
                continue
            alts.append(
                {
                    "id": pid,
                    "label": f"Vault · {row.kind or row.category} ({row.label or row.id[:8]})",
                    "model": None,
                    "source": "vault",
                    "vault_id": row.id,
                }
            )
            seen.add(pid)
    except Exception:
        pass

    try:
        for p in list_providers(db).get("providers") or []:
            pid = f"workspace_{p.get('id')}"
            if pid in seen:
                continue
            alts.append(
                {
                    "id": pid,
                    "label": _label_for_source(
                        p.get("name") or p.get("provider_type") or "Workspace",
                        p.get("chat_model") or "",
                    ),
                    "model": p.get("chat_model"),
                    "source": "workspace",
                    "provider_row_id": p.get("id"),
                }
            )
            seen.add(pid)
    except Exception:
        pass

    return alts


def resolve_chat_llm_config(
    db: Session,
    workspace_id: int,
    user_id: int,
    aios: dict[str, Any] | None = None,
    *,
    strict_user_key: bool = False,
) -> dict[str, Any]:
    aios = aios or {}
    alternatives = list_llm_alternatives(db, workspace_id, user_id, aios)

    override = aios.get("planning_override") or {}
    if override.get("api_key"):
        return {
            **override,
            "source": "override",
            "planning_label": _label_for_source(override.get("provider_name") or "Override", override.get("model") or ""),
            "available_alternatives": alternatives,
        }

    if override.get("provider_row_id"):
        from app.database import LlmProvider
        from app.services.llm_providers import resolve_api_key

        row = db.get(LlmProvider, int(override["provider_row_id"]))
        if row:
            ptype = (row.provider_type or "openai").lower()
            meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openai"])
            model = override.get("model") or row.chat_model or meta["default_chat"]
            return {
                "provider_id": f"workspace_{row.id}",
                "provider_type": ptype,
                "provider_name": row.name or ptype,
                "api_key": resolve_api_key(row),
                "base_url": (row.base_url or meta["base_url"]).rstrip("/"),
                "model": model,
                "embedding_model": row.embedding_model or meta.get("default_embedding"),
                "source": "workspace",
                "planning_label": _label_for_source(row.name or ptype, model),
                "available_alternatives": alternatives,
            }

    conv_key = aios.get("conversation_api_key")
    if conv_key:
        cfg = get_active_config(db, conversation_api_key=conv_key, user_id=user_id)
        cfg["source"] = "conversation"
        cfg["planning_label"] = _label_for_source(cfg.get("provider_name") or "Chat paste", cfg.get("model") or "")
        cfg["available_alternatives"] = alternatives
        return cfg

    from app.services.user_management import UserApiKeyManager

    mgr = UserApiKeyManager(db)
    user_key = mgr.get_user_api_key(user_id)
    if user_key:
        user_cfg = mgr.get_user_api_config(user_id)
        ptype = user_cfg.get("provider", "openrouter")
        meta = PROVIDER_TYPES.get(ptype, PROVIDER_TYPES["openrouter"])
        model = aios.get("planning_model") or mgr.get_model_for_user(user_id) or meta["default_chat"]
        return {
            "provider_id": f"user_{user_id}",
            "provider_type": ptype,
            "provider_name": f"Your {ptype} key",
            "api_key": user_key,
            "base_url": mgr.get_base_url_for_user(user_id),
            "model": model,
            "embedding_model": meta.get("default_embedding"),
            "source": "user",
            "planning_label": _label_for_source(f"Your {ptype} key", model),
            "available_alternatives": alternatives,
        }

    if strict_user_key:
        return {
            "api_key": "",
            "source": "none",
            "planning_label": "No user API key — add one in Settings",
            "available_alternatives": alternatives,
            "error": "user_api_key_required",
        }

    try:
        db._workspace_id = workspace_id  # type: ignore[attr-defined]
    except Exception:
        pass
    cfg = get_active_config(db, user_id=user_id)
    src = "workspace"
    if cfg.get("provider_id") == "vault":
        src = "vault"
    elif cfg.get("provider_id") and str(cfg.get("provider_id")).startswith("user_"):
        src = "user"
    cfg["source"] = src
    if aios.get("planning_model"):
        cfg["model"] = aios["planning_model"]
    cfg["planning_label"] = _label_for_source(cfg.get("provider_name") or "Workspace LLM", cfg.get("model") or "")
    cfg["available_alternatives"] = alternatives
    return cfg


def apply_planning_model_switch(aios: dict[str, Any], text: str, db: Session, workspace_id: int, user_id: int) -> bool:
    t = (text or "").lower().strip()
    m = re.search(r"\b(?:use|switch to)\s+(?:model\s+)?([a-z0-9][a-z0-9._\-/]{2,60})\b", t, re.I)
    if not m:
        return False
    model = m.group(1).strip()
    cfg = resolve_chat_llm_config(db, workspace_id, user_id, aios)
    override = {
        "api_key": cfg.get("api_key"),
        "base_url": cfg.get("base_url"),
        "model": model,
        "provider_id": cfg.get("provider_id"),
        "provider_type": cfg.get("provider_type"),
        "provider_name": cfg.get("provider_name"),
    }
    aios["planning_override"] = override
    aios["planning_model"] = model
    aios["planning_source"] = "override"
    aios["planning_label"] = _label_for_source(override.get("provider_name") or "LLM", model)
    return True
