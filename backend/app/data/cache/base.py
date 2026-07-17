"""Tenant-aware cache interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheProvider(ABC):
    name: str = "base"

    def tenant_key(self, workspace_id: int | None, *parts: str) -> str:
        from app.platform.worker import tenant_cache_key

        if workspace_id is None:
            return "nf:global:" + ":".join(str(p) for p in parts)
        return tenant_cache_key(workspace_id, *parts)

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None, tags: list[str] | None = None) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def invalidate_tags(self, tags: list[str]) -> int:
        ...

    def get_or_set(self, key: str, factory, *, ttl_seconds: int | None = 60, tags: list[str] | None = None):
        """Read-through with simple stampede protection (single-flight lock when available)."""
        val = self.get(key)
        if val is not None:
            return val
        if hasattr(self, "lock"):
            with self.lock(f"lock:{key}", timeout=5):  # type: ignore[attr-defined]
                val = self.get(key)
                if val is not None:
                    return val
                val = factory()
                self.set(key, val, ttl_seconds=ttl_seconds, tags=tags)
                return val
        val = factory()
        self.set(key, val, ttl_seconds=ttl_seconds, tags=tags)
        return val
