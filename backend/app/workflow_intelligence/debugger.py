"""Workflow debugger — timeline, replay, state inspection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.database import WorkflowRun


@dataclass
class TimelineEvent:
    node_id: str
    node_type: str
    status: str
    output_preview: str = ""
    duration_ms: float | None = None
    index: int = 0


@dataclass
class DebugSession:
    run_id: int
    workflow_id: str
    timeline: list[TimelineEvent] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "timeline": [e.__dict__ for e in self.timeline],
            "variables": self.variables,
            "dependency_graph": self.dependency_graph,
        }


def build_debug_session(db: Session, run: WorkflowRun, graph: dict | None = None) -> DebugSession:
    try:
        steps = json.loads(run.steps_json or "[]")
    except json.JSONDecodeError:
        steps = []

    timeline: list[TimelineEvent] = []
    variables: dict[str, Any] = {"input": run.input_text or "", "output": run.output_text or ""}

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        timeline.append(
            TimelineEvent(
                node_id=str(step.get("node_id") or ""),
                node_type=str(step.get("type") or ""),
                status=str(step.get("status") or ""),
                output_preview=str(step.get("output") or "")[:500],
                index=i,
            )
        )
        if step.get("type") == "retrieve" and step.get("hits") is not None:
            variables["retrieved_hits"] = step.get("hits")
        if step.get("type") == "agent" and step.get("tool_results"):
            variables["agent_tools"] = step.get("tool_results")

    dep: dict[str, list[str]] = {}
    if graph:
        for e in graph.get("edges") or []:
            fr = e.get("from")
            to = e.get("to")
            if fr and to:
                dep.setdefault(fr, []).append(to)

    return DebugSession(
        run_id=int(run.id),
        workflow_id=str(run.workflow_id),
        timeline=timeline,
        variables=variables,
        dependency_graph=dep,
    )


def replay_steps(steps: list[dict]) -> list[dict]:
    """Return steps up to first error for replay analysis."""
    out = []
    for step in steps:
        out.append(step)
        if isinstance(step, dict) and step.get("status") == "error":
            break
    return out
