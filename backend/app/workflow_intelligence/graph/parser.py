"""Parse raw graph JSON into typed WorkflowGraph."""

from __future__ import annotations

import json
from typing import Any

from app.workflow_intelligence.graph.model import WorkflowEdge, WorkflowGraph, WorkflowNode


def parse_graph(raw: str | dict | None) -> WorkflowGraph:
    if raw is None:
        return WorkflowGraph()
    if isinstance(raw, str):
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return WorkflowGraph()
    else:
        data = raw

    nodes: list[WorkflowNode] = []
    for row in data.get("nodes") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("id") or "").strip()
        if not nid:
            continue
        nodes.append(
            WorkflowNode(
                id=nid,
                type=str(row.get("type") or "unknown").strip().lower(),
                data=dict(row.get("data") or {}),
                x=float(row.get("x") or 0),
                y=float(row.get("y") or 0),
            )
        )

    edges: list[WorkflowEdge] = []
    for row in data.get("edges") or []:
        if not isinstance(row, dict):
            continue
        fr = str(row.get("from") or "").strip()
        to = str(row.get("to") or "").strip()
        if fr and to:
            edges.append(WorkflowEdge(from_id=fr, to_id=to))

    return WorkflowGraph(nodes=nodes, edges=edges)
