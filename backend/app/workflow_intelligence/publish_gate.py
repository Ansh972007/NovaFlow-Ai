"""Pre-publish gate — blocks publish when validation/security fail."""

from __future__ import annotations

from typing import Any

from app.workflow_intelligence.graph.model import WorkflowGraph
from app.workflow_intelligence.graph.validator import validate_graph
from app.workflow_intelligence.optimizer import optimize_graph
from app.workflow_intelligence.security import validate_workflow_security


def check_publish_ready(graph: WorkflowGraph, *, block_on_warnings: bool = False) -> dict[str, Any]:
    validation = validate_graph(graph, strict=True)
    security = validate_workflow_security(graph)
    optimization = optimize_graph(graph)

    errors = [i for i in validation.issues if i.severity == "error"]
    warnings = [i for i in validation.issues if i.severity == "warning"]
    sec_errors = [f for f in security.findings if f.severity == "error"]

    ready = not errors and not sec_errors
    if block_on_warnings and warnings:
        ready = False

    return {
        "ready": ready,
        "validation": validation.to_dict(),
        "security": security.to_dict(),
        "optimization": optimization.to_dict(),
        "blockers": [
            *[{"source": "validation", **i.__dict__} for i in errors],
            *[{"source": "security", **f.__dict__} for f in sec_errors],
        ],
    }
