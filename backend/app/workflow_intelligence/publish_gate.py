"""Pre-publish gate — blocks publish when validation/security fail."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.workflow_intelligence.graph.model import WorkflowGraph
from app.workflow_intelligence.graph.validator import validate_graph
from app.workflow_intelligence.optimizer import optimize_graph
from app.workflow_intelligence.security import validate_workflow_security


def check_publish_ready(
    graph: WorkflowGraph,
    *,
    block_on_warnings: bool = False,
    db: Session | None = None,
    workspace_id: int | None = None,
) -> dict[str, Any]:
    validation = validate_graph(graph, workspace_id=workspace_id, strict=True)
    security = validate_workflow_security(graph)
    optimization = optimize_graph(graph)

    api_node_blockers: list[dict[str, Any]] = []
    if db and workspace_id:
        from app.services.node_library import validate_graph_api_nodes

        raw_graph = {
            "nodes": [
                {"id": n.id, "type": n.type, "data": n.data or {}}
                for n in graph.nodes
            ],
            "edges": [{"from": e.from_id, "to": e.to_id} for e in graph.edges],
        }
        api_node_blockers = validate_graph_api_nodes(db, workspace_id, raw_graph)

    errors = [i for i in validation.issues if i.severity == "error"]
    warnings = [i for i in validation.issues if i.severity == "warning"]
    sec_errors = [f for f in security.findings if f.severity == "error"]

    ready = not errors and not sec_errors and not api_node_blockers
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
            *[{"source": "node_library", **b} for b in api_node_blockers],
        ],
    }
