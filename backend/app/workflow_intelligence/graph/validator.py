"""Workflow graph validator — pre-publish quality gate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.workflow_intelligence.graph.model import KNOWN_NODE_TYPES, WorkflowGraph


@dataclass
class ValidationIssue:
    code: str
    severity: str  # error | warning | suggestion
    message: str
    node_id: str = ""
    field: str = ""


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "score": round(self.score, 1),
            "error_count": sum(1 for i in self.issues if i.severity == "error"),
            "warning_count": sum(1 for i in self.issues if i.severity == "warning"),
            "suggestion_count": sum(1 for i in self.issues if i.severity == "suggestion"),
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "node_id": i.node_id,
                    "field": i.field,
                }
                for i in self.issues
            ],
        }


def _detect_cycles(graph: WorkflowGraph) -> list[list[str]]:
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        if e.from_id in adj:
            adj[e.from_id].append(e.to_id)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: set[str] = set()
    path: list[str] = []

    def dfs(nid: str) -> None:
        if nid in stack:
            if nid in path:
                idx = path.index(nid)
                cycles.append(path[idx:] + [nid])
            return
        if nid in visited:
            return
        visited.add(nid)
        stack.add(nid)
        path.append(nid)
        for nxt in adj.get(nid, []):
            dfs(nxt)
        path.pop()
        stack.discard(nid)

    for nid in adj:
        dfs(nid)
    return cycles


def _reachable_from_triggers(graph: WorkflowGraph) -> set[str]:
    triggers = [n.id for n in graph.nodes if n.type == "trigger"]
    if not triggers and graph.nodes:
        triggers = [graph.nodes[0].id]

    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        if e.from_id in adj:
            adj[e.from_id].append(e.to_id)

    seen: set[str] = set()
    queue = list(triggers)
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        queue.extend(adj.get(nid, []))
    return seen


def validate_graph(
    graph: WorkflowGraph,
    *,
    workspace_id: int | None = None,
    strict: bool = False,
) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not graph.nodes:
        issues.append(ValidationIssue("empty_graph", "error", "Workflow has no nodes"))
        return ValidationReport(ok=False, issues=issues, score=0)

    ids = graph.node_ids
    id_counts: dict[str, int] = {}
    for n in graph.nodes:
        id_counts[n.id] = id_counts.get(n.id, 0) + 1
        if id_counts[n.id] > 1:
            issues.append(
                ValidationIssue("duplicate_node_id", "error", f"Duplicate node id: {n.id}", node_id=n.id)
            )
        if n.type not in KNOWN_NODE_TYPES:
            issues.append(
                ValidationIssue(
                    "unknown_node_type",
                    "error" if strict else "warning",
                    f"Unknown node type: {n.type}",
                    node_id=n.id,
                )
            )

    for e in graph.edges:
        if e.from_id not in ids:
            issues.append(
                ValidationIssue("dangling_edge", "error", f"Edge from unknown node: {e.from_id}", node_id=e.from_id)
            )
        if e.to_id not in ids:
            issues.append(
                ValidationIssue("dangling_edge", "error", f"Edge to unknown node: {e.to_id}", node_id=e.to_id)
            )
        if e.from_id == e.to_id:
            issues.append(
                ValidationIssue("self_loop", "error", f"Self-loop on node {e.from_id}", node_id=e.from_id)
            )

    cycles = _detect_cycles(graph)
    for cycle in cycles:
        issues.append(
            ValidationIssue(
                "cycle_detected",
                "error",
                f"Circular execution: {' → '.join(cycle)}",
                node_id=cycle[0] if cycle else "",
            )
        )

    reachable = _reachable_from_triggers(graph)
    for n in graph.nodes:
        if n.id not in reachable:
            issues.append(
                ValidationIssue("unreachable_node", "warning", f"Node is unreachable: {n.id}", node_id=n.id)
            )

    connected = set()
    for e in graph.edges:
        connected.add(e.from_id)
        connected.add(e.to_id)
    for n in graph.nodes:
        if n.id not in connected and len(graph.nodes) > 1:
            issues.append(
                ValidationIssue("disconnected_node", "warning", f"Node has no edges: {n.id}", node_id=n.id)
            )

    triggers = [n for n in graph.nodes if n.type == "trigger"]
    if not triggers:
        issues.append(ValidationIssue("missing_trigger", "warning", "No trigger node — first node will be used"))
    outputs = [n for n in graph.nodes if n.type == "output"]
    if not outputs:
        issues.append(ValidationIssue("missing_output", "suggestion", "Consider adding an output node"))

    for n in graph.nodes:
        data = n.data or {}
        if n.type == "retrieve" and not data.get("knowledge_id"):
            issues.append(
                ValidationIssue(
                    "missing_knowledge",
                    "warning",
                    "Retrieve node has no knowledge base linked",
                    node_id=n.id,
                    field="knowledge_id",
                )
            )
        if n.type == "http":
            url = str(data.get("url") or "")
            if not url.strip():
                issues.append(
                    ValidationIssue("missing_url", "error", "HTTP node missing URL", node_id=n.id, field="url")
                )
            elif "{{" not in url and not re.match(r"^https?://", url, re.I):
                issues.append(
                    ValidationIssue("invalid_url", "warning", "HTTP URL may be invalid", node_id=n.id, field="url")
                )
        if n.type == "agent":
            tools = data.get("tools") or []
            if not tools:
                issues.append(
                    ValidationIssue("no_agent_tools", "suggestion", "Agent node has no tools", node_id=n.id)
                )
        if n.type == "subgraph" and not data.get("workflow_id"):
            issues.append(
                ValidationIssue("missing_subgraph", "error", "Subgraph node missing workflow_id", node_id=n.id)
            )
        if n.type == "api_node" and not data.get("node_def_id"):
            issues.append(
                ValidationIssue(
                    "missing_node_def_id",
                    "error",
                    "API node missing node_def_id",
                    node_id=n.id,
                    field="node_def_id",
                )
            )
        if n.type == "loop":
            mx = int(data.get("max") or 5)
            if mx > 20:
                issues.append(
                    ValidationIssue("large_loop", "warning", f"Loop max={mx} may cause long runs", node_id=n.id)
                )
        tmpl = str(data.get("template") or data.get("prompt") or data.get("body") or "")
        if "{{" in tmpl and "}}" not in tmpl:
            issues.append(
                ValidationIssue("invalid_expression", "error", "Unclosed template expression", node_id=n.id)
            )

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    score = max(0.0, 100.0 - error_count * 15 - warning_count * 5)
    ok = error_count == 0 if strict else error_count == 0
    return ValidationReport(ok=ok, issues=issues, score=score)
