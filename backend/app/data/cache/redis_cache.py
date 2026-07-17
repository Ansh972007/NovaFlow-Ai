"""Redis cache — tenant-aware keys, tags via sets, distributed locks."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Optional

from app.data.cache.base import CacheProvider

logger = logging.getLogger(__name__)


class RedisCache(CacheProvider):
    name = "redis"

    def __init__(self, url: str):
        self.url = url
        self._client = None

    def _conn(self):
        if self._client is not None:
            return self._client
        import redis

        self._client = redis.from_url(self.url, decode_responses=True)
        self._client.ping()
        return self._client

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self._conn().get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis get failed: %s", exc)
            return None

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None, tags: list[str] | None = None) -> None:
        try:
            c = self._conn()
            payload = json.dumps(value, default=str)
            if ttl_seconds:
                c.setex(key, int(ttl_seconds), payload)
            else:
                c.set(key, payload)
            for t in tags or []:
                tag_key = f"nf:tag:{t}"
                c.sadd(tag_key, key)
                if ttl_seconds:
                    c.expire(tag_key, int(ttl_seconds) + 60)
        except Exception as exc:
            logger.warning("Redis set failed: %s", exc)

    def delete(self, key: str) -> None:
        try:
            self._conn().delete(key)
        except Exception as exc:
            logger.warning("Redis delete failed: %s", exc)

    def invalidate_tags(self, tags: list[str]) -> int:
        n = 0
        try:
            c = self._conn()
            for t in tags:
                tag_key = f"nf:tag:{t}"
                keys = list(c.smembers(tag_key) or [])
                if keys:
                    n += c.delete(*keys)
                c.delete(tag_key)
        except Exception as exc:
            logger.warning("Redis invalidate_tags failed: %s", exc)
        return n

    @contextmanager
    def lock(self, name: str, timeout: float = 5):
        token = uuid.uuid4().hex
        key = f"nf:lock:{name}"
        c = self._conn()
        end = time.time() + timeout
        acquired = False
        while time.time() < end:
            if c.set(key, token, nx=True, ex=int(timeout) + 1):
                acquired = True
                break
            time.sleep(0.05)
        if not acquired:
            raise TimeoutError(name)
        try:
            yield
        finally:
            # delete only if we own the lock
            lua = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
            try:
                c.eval(lua, 1, key, token)
            except Exception:
                pass
