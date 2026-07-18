"""Typed workflow graph model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


KNOWN_NODE_TYPES = frozenset(
    {
        "trigger",
        "retrieve",
        "transform",
        "condition",
        "http",
        "notify",
        "jira",
        "github",
        "linear",
        "llm",
        "output",
        "loop",
        "parallel",
        "human",
        "agent",
        "subgraph",
    }
)


@dataclass
class WorkflowNode:
    id: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    x: float = 0
    y: float = 0


@dataclass
class WorkflowEdge:
    from_id: str
    to_id: str


@dataclass
class WorkflowGraph:
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)

    @property
    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def node_map(self) -> dict[str, WorkflowNode]:
        return {n.id: n for n in self.nodes}

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "type": n.type, "x": n.x, "y": n.y, "data": n.data} for n in self.nodes
            ],
            "edges": [{"from": e.from_id, "to": e.to_id} for e in self.edges],
        }
