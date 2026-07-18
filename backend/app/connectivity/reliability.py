"""ECP reliability — retries, circuit breakers, idempotency."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from app.platform_intelligence.healing.circuit_breaker import CircuitBreaker


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(key: str) -> CircuitBreaker:
    if key not in _breakers:
        _breakers[key] = CircuitBreaker(name=key)
    return _breakers[key]


def with_retry(
    fn: Callable[[], Any],
    *,
    max_retries: int = 3,
    backoff_ms: int = 200,
) -> Any:
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            time.sleep(backoff_ms / 1000 * (attempt + 1))
    raise last_exc


def idempotency_key(*parts: str) -> str:
    raw = "|".join(p for p in parts if p)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
