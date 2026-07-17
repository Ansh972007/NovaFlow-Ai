"""Database observability hooks — slow queries, counters, health snapshots."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("novaflow.data.observability")

SLOW_QUERY_MS = 200


@dataclass
class QuerySample:
    statement: str
    duration_ms: float
    ts: float


@dataclass
class DbMetrics:
    query_count: int = 0
    slow_count: int = 0
    error_count: int = 0
    total_ms: float = 0.0
    slow_samples: Deque[QuerySample] = field(default_factory=lambda: deque(maxlen=50))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> dict:
        with self._lock:
            avg = (self.total_ms / self.query_count) if self.query_count else 0.0
            return {
                "query_count": self.query_count,
                "slow_count": self.slow_count,
                "error_count": self.error_count,
                "avg_ms": round(avg, 2),
                "slow_queries": [
                    {"statement": s.statement[:240], "duration_ms": round(s.duration_ms, 2)}
                    for s in list(self.slow_samples)
                ],
            }


_metrics = DbMetrics()


def get_db_metrics() -> dict:
    return _metrics.snapshot()


def attach_engine_metrics(engine: Engine, *, slow_ms: float = SLOW_QUERY_MS) -> None:
    """Listen for before/after cursor execute to track latency."""

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        conn.info["nf_query_start"] = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        start = conn.info.pop("nf_query_start", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000
        with _metrics._lock:
            _metrics.query_count += 1
            _metrics.total_ms += duration_ms
            if duration_ms >= slow_ms:
                _metrics.slow_count += 1
                _metrics.slow_samples.append(
                    QuerySample(statement=str(statement), duration_ms=duration_ms, ts=time.time())
                )
                logger.warning("Slow query %.1fms: %s", duration_ms, str(statement)[:200])

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context):  # noqa: ANN001
        with _metrics._lock:
            _metrics.error_count += 1


def optimization_report() -> dict:
    """Lightweight report for operators — extend with pg_stat_statements in PG ops."""
    snap = get_db_metrics()
    tips = []
    if snap["slow_count"] > 0:
        tips.append("Investigate slow_queries; consider tenant composite indexes (workspace_id, create_time).")
    if snap["avg_ms"] > 50:
        tips.append("Average query latency elevated — check N+1 patterns and connection pool saturation.")
    if snap["error_count"] > 0:
        tips.append("Database errors observed — check deadlock retries and statement_timeout.")
    return {"metrics": snap, "recommendations": tips}
