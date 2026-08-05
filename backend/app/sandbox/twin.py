"""Sandbox twin — lightweight simulated trial of a workflow / solution graph."""

from __future__ import annotations

import random
from typing import Any


def _iter_nodes(graph_payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Normalize nodes as (id, data) whether payload uses dict or list form."""
    nodes = graph_payload.get("nodes") or {}
    if isinstance(nodes, dict):
        return [(str(k), v if isinstance(v, dict) else {"raw": v}) for k, v in nodes.items()]
    if isinstance(nodes, list):
        out: list[tuple[str, dict[str, Any]]] = []
        for i, n in enumerate(nodes):
            if not isinstance(n, dict):
                continue
            nid = str(n.get("id") or n.get("type") or f"node_{i}")
            out.append((nid, n))
        return out
    return []


def run_sandbox_trial(graph_payload: dict, inject_error_node: str = "") -> dict:
    """Simulates execution of a Solution / Workflow graph, tracking latency and errors."""
    logs: list[str] = []
    total_latency_ms = 0
    status = "success"
    node_results: list[dict[str, Any]] = []

    for node_id, node_data in _iter_nodes(graph_payload or {}):
        ntype = str(node_data.get("type") or "unknown")
        if inject_error_node and inject_error_node == node_id:
            logs.append(f"Node [{node_id}] ({ntype}): Injected error triggered!")
            node_results.append({"id": node_id, "type": ntype, "status": "failed"})
            status = "failed"
            break

        node_latency = random.randint(50, 150)
        total_latency_ms += node_latency
        logs.append(f"Node [{node_id}] ({ntype}): Executed successfully in {node_latency}ms")
        node_results.append(
            {"id": node_id, "type": ntype, "status": "ok", "latency_ms": node_latency}
        )

    return {
        "status": status,
        "total_latency_ms": total_latency_ms,
        "logs": logs,
        "nodes": node_results,
        "node_count": len(node_results),
        "performance_profile": "optimal" if total_latency_ms < 1000 else "warning_latency",
    }
