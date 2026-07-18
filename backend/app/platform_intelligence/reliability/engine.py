"""Reliability engine — retry policies, health checks, recovery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class ReliabilityPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 500
    max_delay_ms: int = 8000
    backoff_factor: float = 2.0
    fallback: str = ""


async def execute_with_reliability(
    fn: Callable[[], Awaitable[Any]],
    *,
    policy: ReliabilityPolicy | None = None,
    breaker_name: str = "default",
    label: str = "operation",
) -> tuple[Any, dict[str, Any]]:
    from app.platform_intelligence.healing.circuit_breaker import get_breaker

    policy = policy or ReliabilityPolicy()
    br = get_breaker(breaker_name)
    meta = {"attempts": 0, "retries": 0, "breaker_state": br.state}

    if not br.allow():
        raise RuntimeError(f"Circuit breaker open: {breaker_name}")

    delay = policy.base_delay_ms / 1000.0
    last_exc: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        meta["attempts"] = attempt
        try:
            result = await fn()
            br.record_success()
            meta["retries"] = attempt - 1
            return result, meta
        except Exception as exc:
            last_exc = exc
            br.record_failure()
            meta["retries"] = attempt
            if attempt >= policy.max_attempts:
                break
            await asyncio.sleep(delay)
            delay = min(delay * policy.backoff_factor, policy.max_delay_ms / 1000.0)

    raise last_exc or RuntimeError(f"{label} failed after {policy.max_attempts} attempts")
