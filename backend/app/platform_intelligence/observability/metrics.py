"""Platform metrics collection and persistence."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

# In-memory ring buffer for fast dashboard (last N samples)
_RING: list[dict] = []
_RING_MAX = 500


@dataclass
class MetricSample:
    subsystem: str
    operation: str
    trace_id: str = ""
    workspace_id: int | None = None
    organization_id: int | None = None
    latency_ms: float = 0.0
    status: str = "ok"
    provider: str = ""
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    knowledge_hits: int = 0
    queue_ms: float = 0.0
    retries: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def _ring_append(sample: dict) -> None:
    global _RING
    _RING.append(sample)
    if len(_RING) > _RING_MAX:
        _RING = _RING[-_RING_MAX:]


def record_http_metric(
    *,
    path: str,
    method: str,
    status: int,
    latency_ms: float,
    trace_id: str,
    workspace_id: int | None = None,
) -> None:
    sample = {
        "subsystem": "http",
        "operation": f"{method} {path}",
        "trace_id": trace_id,
        "workspace_id": workspace_id,
        "latency_ms": round(latency_ms, 2),
        "status": "ok" if status < 400 else "error",
        "http_status": status,
        "ts": time.time(),
    }
    _ring_append(sample)


def record_runtime_metric(db: Session | None, sample: MetricSample) -> None:
    payload = {
        "subsystem": sample.subsystem,
        "operation": sample.operation,
        "trace_id": sample.trace_id,
        "workspace_id": sample.workspace_id,
        "organization_id": sample.organization_id,
        "latency_ms": round(sample.latency_ms, 2),
        "status": sample.status,
        "provider": sample.provider,
        "model": sample.model,
        "prompt_tokens": sample.prompt_tokens,
        "completion_tokens": sample.completion_tokens,
        "cost_usd": sample.cost_usd,
        "knowledge_hits": sample.knowledge_hits,
        "queue_ms": sample.queue_ms,
        "retries": sample.retries,
        "ts": time.time(),
        **sample.extra,
    }
    _ring_append(payload)

    if db is None:
        return
    try:
        from app.database import PlatformMetric

        row = PlatformMetric(
            subsystem=sample.subsystem,
            operation=sample.operation,
            trace_id=sample.trace_id or "",
            workspace_id=sample.workspace_id,
            organization_id=sample.organization_id,
            latency_ms=int(sample.latency_ms),
            status=sample.status,
            provider=sample.provider or "",
            model=sample.model or "",
            prompt_tokens=sample.prompt_tokens,
            completion_tokens=sample.completion_tokens,
            cost_usd=sample.cost_usd,
            meta_json=json.dumps({k: v for k, v in payload.items() if k not in ("ts",)}),
        )
        db.add(row)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def get_recent_metrics(*, subsystem: str | None = None, limit: int = 100) -> list[dict]:
    rows = _RING[-limit:]
    if subsystem:
        rows = [r for r in rows if r.get("subsystem") == subsystem]
    return list(reversed(rows))


def aggregate_subsystems(limit: int = 200) -> dict[str, Any]:
    rows = _RING[-limit:]
    by_sub: dict[str, dict] = {}
    for r in rows:
        sub = r.get("subsystem") or "unknown"
        bucket = by_sub.setdefault(sub, {"count": 0, "errors": 0, "latency_sum": 0.0, "cost_sum": 0.0})
        bucket["count"] += 1
        if r.get("status") == "error":
            bucket["errors"] += 1
        bucket["latency_sum"] += float(r.get("latency_ms") or 0)
        if r.get("cost_usd"):
            bucket["cost_sum"] += float(r["cost_usd"])
    out = {}
    for sub, b in by_sub.items():
        out[sub] = {
            "count": b["count"],
            "error_rate": round(b["errors"] / b["count"], 3) if b["count"] else 0,
            "avg_latency_ms": round(b["latency_sum"] / b["count"], 1) if b["count"] else 0,
            "cost_usd": round(b["cost_sum"], 6),
        }
    return out
