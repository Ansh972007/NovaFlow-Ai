"""Self-healing — circuit breakers and failure detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_seconds: float = 60.0
    failures: int = 0
    last_failure: float = 0.0
    state: str = "closed"  # closed | open | half_open

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def allow(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure >= self.recovery_seconds:
                self.state = "half_open"
                return True
            return False
        return True  # half_open — allow probe


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]


def breaker_status() -> dict[str, Any]:
    return {
        name: {"state": b.state, "failures": b.failures, "threshold": b.failure_threshold}
        for name, b in _breakers.items()
    }


def with_circuit_breaker(name: str):
    """Decorator for async/sync callables."""

    def decorator(fn):
        async def async_wrapper(*args, **kwargs):
            br = get_breaker(name)
            if not br.allow():
                raise RuntimeError(f"Circuit breaker open: {name}")
            try:
                result = await fn(*args, **kwargs)
                br.record_success()
                return result
            except Exception:
                br.record_failure()
                raise

        return async_wrapper

    return decorator
