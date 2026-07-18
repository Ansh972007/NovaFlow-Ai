"""Workflow execution observability."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.database import WorkflowRun


@dataclass
class RunMetrics:
    run_id: int
    workflow_id: str
    duration_ms: int = 0
    step_count: int = 0
    error_count: int = 0
    llm_steps: int = 0
    retrieve_steps: int = 0
    per_node_latency: dict[str, float] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "duration_ms": self.duration_ms,
            "step_count": self.step_count,
            "error_count": self.error_count,
            "llm_steps": self.llm_steps,
            "retrieve_steps": self.retrieve_steps,
            "per_node_latency": self.per_node_latency,
            "trace_id": self.trace_id,
        }


def analyze_run(run: WorkflowRun) -> RunMetrics:
    try:
        steps = json.loads(run.steps_json or "[]")
    except json.JSONDecodeError:
        steps = []

    metrics = RunMetrics(
        run_id=int(run.id),
        workflow_id=str(run.workflow_id),
        duration_ms=int(run.duration_ms or 0),
        step_count=len(steps),
    )
    for step in steps:
        if not isinstance(step, dict):
            continue
        st = step.get("status")
        if st == "error":
            metrics.error_count += 1
        ntype = step.get("type")
        if ntype == "llm" or ntype == "agent":
            metrics.llm_steps += 1
        if ntype == "retrieve":
            metrics.retrieve_steps += 1
        if step.get("duration_ms") is not None:
            metrics.per_node_latency[str(step.get("node_id") or "")] = float(step["duration_ms"])
        if step.get("trace_id"):
            metrics.trace_id = str(step["trace_id"])
    return metrics


def workspace_run_stats(db: Session, workspace_id: int, *, limit: int = 100) -> dict[str, Any]:
    rows = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workspace_id == workspace_id)
        .order_by(WorkflowRun.create_time.desc())
        .limit(limit)
        .all()
    )
    total = len(rows)
    errors = sum(1 for r in rows if int(r.status or 1) == 2)
    durations = [int(r.duration_ms or 0) for r in rows if r.duration_ms]
    avg_ms = sum(durations) / len(durations) if durations else 0
    return {
        "total_runs": total,
        "error_rate": round(errors / total, 3) if total else 0,
        "avg_duration_ms": round(avg_ms, 1),
        "success_rate": round((total - errors) / total, 3) if total else 1,
    }
