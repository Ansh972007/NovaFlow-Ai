"""Cache registry — Redis when configured, else memory."""

from __future__ import annotations

from app.data.cache.base import CacheProvider
from app.data.cache.memory import MemoryCache
from app.data.cache.redis_cache import RedisCache
from app.data.config import load_data_config

_cache: CacheProvider | None = None


def get_cache(*, reset: bool = False) -> CacheProvider:
    global _cache
    if reset or _cache is None:
        cfg = load_data_config()
        if cfg.redis_url:
            try:
                c = RedisCache(cfg.redis_url)
                c._conn()  # validate
                _cache = c
            except Exception:
                _cache = MemoryCache()
        else:
            _cache = MemoryCache()
    return _cache
