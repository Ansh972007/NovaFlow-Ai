"""Bridge runtime/workflow telemetry to Platform Intelligence."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.context import RuntimeContext
    from app.runtime.observability import RuntimeMetrics


def record_ai_telemetry(ctx: "RuntimeContext", metrics: "RuntimeMetrics", *, operation: str) -> None:
    from app.platform_intelligence.finops.ledger import record_llm_cost_from_metrics
    from app.platform_intelligence.observability.metrics import MetricSample, record_runtime_metric
    from app.platform_intelligence.tracing.context import get_trace_id

    trace = metrics.trace_id or get_trace_id()
    sample = MetricSample(
        subsystem="ai_runtime",
        operation=operation,
        trace_id=trace,
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        latency_ms=metrics.latency_ms,
        status="error" if metrics.errors else "ok",
        provider=metrics.provider,
        model=metrics.model,
        prompt_tokens=metrics.prompt_tokens,
        completion_tokens=metrics.completion_tokens,
        cost_usd=metrics.cost_usd,
        knowledge_hits=metrics.knowledge_hits,
        retries=metrics.retries,
    )
    record_runtime_metric(ctx.db, sample)
    if metrics.cost_usd:
        record_llm_cost_from_metrics(
            ctx.db,
            workspace_id=ctx.workspace_id,
            organization_id=ctx.organization_id,
            model=metrics.model,
            prompt_tokens=metrics.prompt_tokens,
            completion_tokens=metrics.completion_tokens,
            trace_id=trace,
            resource_type=operation,
        )
