"""Streaming runtime — SSE/WebSocket chunk streaming with cancellation."""

from __future__ import annotations

from typing import AsyncIterator

from app.runtime.context import RuntimeContext
from app.runtime.execution import execute_chat_stream
from app.runtime.observability import MetricsTimer, RuntimeMetrics, enrich_cost
from app.runtime.validation import validate_markdown_output


async def stream_runtime_response(
    ctx: RuntimeContext,
    system: str,
    user: str,
    *,
    history: list[dict] | None = None,
    metrics: RuntimeMetrics | None = None,
    usage_out: dict | None = None,
) -> AsyncIterator[str]:
    """Stream tokens; honour cancel_event on RuntimeContext."""
    timer = MetricsTimer()
    usage: dict = usage_out if usage_out is not None else {}
    async for token in execute_chat_stream(
        ctx,
        system,
        user,
        history=history,
        usage_out=usage,
    ):
        if ctx.cancelled():
            break
        yield token

    if metrics is not None:
        metrics.latency_ms = timer.elapsed_ms()
        metrics.prompt_tokens = usage.get("prompt_tokens")
        metrics.completion_tokens = usage.get("completion_tokens")
        metrics.total_tokens = usage.get("total_tokens")
        metrics.model = usage.get("model") or metrics.model
        enrich_cost(metrics)


def validate_stream_buffer(buffer: str) -> str:
    return validate_markdown_output(buffer).content
