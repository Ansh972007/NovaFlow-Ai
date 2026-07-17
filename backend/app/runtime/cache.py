"""Runtime cache — tenant-aware prompt, embedding, knowledge, model, and tool caches."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.data.cache import get_cache


def _cache():
    return get_cache()


def runtime_cache_key(workspace_id: int, namespace: str, key: str) -> str:
    return _cache().tenant_key(workspace_id, "runtime", namespace, key)


def runtime_cache_get(workspace_id: int, namespace: str, key: str) -> Any | None:
    return _cache().get(runtime_cache_key(workspace_id, namespace, key))


def runtime_cache_set(
    workspace_id: int,
    namespace: str,
    key: str,
    value: Any,
    *,
    ttl_seconds: int = 300,
    tags: list[str] | None = None,
) -> None:
    _cache().set(
        runtime_cache_key(workspace_id, namespace, key),
        value,
        ttl_seconds=ttl_seconds,
        tags=tags or [f"ws:{workspace_id}"],
    )


def prompt_cache_key(system: str, user: str, model: str) -> str:
    digest = hashlib.sha256(f"{model}|{system}|{user}".encode()).hexdigest()[:24]
    return f"prompt:{digest}"


def invalidate_workspace_cache(workspace_id: int) -> int:
    return _cache().invalidate_tags([f"ws:{workspace_id}"])
