"""EIAP model intelligence — benchmark providers, recommend best per task.

Reuses platform_intelligence metrics (PlatformMetric). Never calls providers directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session


def benchmark_models(db: Session, *, workspace_id: int, days: int = 30) -> dict[str, Any]:
    from app.database import PlatformMetric

    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(PlatformMetric)
        .filter(
            PlatformMetric.workspace_id == workspace_id,
            PlatformMetric.create_time >= since,
            PlatformMetric.model != "",
        )
        .all()
    )
    by_model: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = r.model or "unknown"
        b = by_model.setdefault(
            key,
            {"model": key, "provider": r.provider or "", "calls": 0, "errors": 0, "latency_sum": 0, "cost_sum": 0.0, "tokens": 0},
        )
        b["calls"] += 1
        if r.status == "error":
            b["errors"] += 1
        b["latency_sum"] += int(r.latency_ms or 0)
        b["cost_sum"] += float(r.cost_usd or 0)
        b["tokens"] += int((r.prompt_tokens or 0) + (r.completion_tokens or 0))

    benchmarks = []
    for b in by_model.values():
        calls = b["calls"]
        benchmarks.append(
            {
                "model": b["model"],
                "provider": b["provider"],
                "calls": calls,
                "error_rate": round(b["errors"] / calls, 3) if calls else 0,
                "avg_latency_ms": round(b["latency_sum"] / calls, 1) if calls else 0,
                "total_cost_usd": round(b["cost_sum"], 6),
                "avg_cost_per_call": round(b["cost_sum"] / calls, 6) if calls else 0,
                "tokens": b["tokens"],
            }
        )
    benchmarks.sort(key=lambda x: (x["error_rate"], x["avg_latency_ms"], x["avg_cost_per_call"]))
    return {"workspace_id": workspace_id, "days": days, "benchmarks": benchmarks}


def recommend_provider(db: Session, *, workspace_id: int, priority: str = "balanced") -> dict[str, Any]:
    data = benchmark_models(db, workspace_id=workspace_id)
    benchmarks = [b for b in data["benchmarks"] if b["calls"] >= 3]
    if not benchmarks:
        return {"recommendation": None, "reason": "Insufficient telemetry to benchmark models"}

    if priority == "cost":
        best = min(benchmarks, key=lambda b: b["avg_cost_per_call"])
    elif priority == "latency":
        best = min(benchmarks, key=lambda b: b["avg_latency_ms"])
    elif priority == "quality":
        best = min(benchmarks, key=lambda b: b["error_rate"])
    else:
        best = min(benchmarks, key=lambda b: (b["error_rate"], b["avg_latency_ms"], b["avg_cost_per_call"]))

    return {
        "recommendation": best["model"],
        "provider": best["provider"],
        "priority": priority,
        "reason": f"Best {priority} profile: {best['error_rate'] * 100:.1f}% errors, {best['avg_latency_ms']:.0f}ms avg, ${best['avg_cost_per_call']:.5f}/call",
        "candidates": benchmarks[:5],
    }
