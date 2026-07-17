"""In-process cache — development / single-node fallback."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Optional

from app.data.cache.base import CacheProvider


class MemoryCache(CacheProvider):
    name = "memory"

    def __init__(self):
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._tags: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            val, exp = item
            if exp is not None and time.time() > exp:
                del self._data[key]
                return None
            return val

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None, tags: list[str] | None = None) -> None:
        exp = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            self._data[key] = (value, exp)
            for t in tags or []:
                self._tags.setdefault(t, set()).add(key)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def invalidate_tags(self, tags: list[str]) -> int:
        n = 0
        with self._lock:
            for t in tags:
                for key in list(self._tags.get(t, set())):
                    if key in self._data:
                        del self._data[key]
                        n += 1
                self._tags.pop(t, None)
        return n

    @contextmanager
    def lock(self, name: str, timeout: float = 5):
        # Best-effort local lock
        acquired = self._lock.acquire(timeout=timeout)
        try:
            if not acquired:
                raise TimeoutError(name)
            yield
        finally:
            if acquired:
                self._lock.release()
