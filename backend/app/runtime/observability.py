"""Runtime observability — latency, tokens, cost, tool calls, cache hits."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeMetrics:
    trace_id: str = ""
    provider: str = ""
    model: str = ""
    policy: str = ""
    latency_ms: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    knowledge_hits: int = 0
    cache_hit: bool = False
    tool_calls: int = 0
    retries: int = 0
    errors: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "provider": self.provider,
            "model": self.model,
            "policy": self.policy,
            "latency_ms": round(self.latency_ms, 2),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "knowledge_hits": self.knowledge_hits,
            "cache_hit": self.cache_hit,
            "tool_calls": self.tool_calls,
            "retries": self.retries,
            "errors": self.errors,
            **self.extra,
        }


class MetricsTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def enrich_cost(metrics: RuntimeMetrics) -> None:
    from app.services.receipt import estimate_cost_usd

    metrics.cost_usd = estimate_cost_usd(
        metrics.model, metrics.prompt_tokens, metrics.completion_tokens
    )
