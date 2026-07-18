"""Workflow optimizer — suggest parallel execution, caching, cost/latency improvements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.workflow_intelligence.graph.model import WorkflowGraph


@dataclass
class OptimizationSuggestion:
    code: str
    category: str
    message: str
    impact: str = "medium"  # low | medium | high
    node_ids: list[str] = field(default_factory=list)


@dataclass
class OptimizationReport:
    suggestions: list[OptimizationSuggestion] = field(default_factory=list)
    estimated_llm_calls: int = 0
    parallelizable_groups: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_llm_calls": self.estimated_llm_calls,
            "parallelizable_groups": self.parallelizable_groups,
            "suggestions": [
                {
                    "code": s.code,
                    "category": s.category,
                    "message": s.message,
                    "impact": s.impact,
                    "node_ids": s.node_ids,
                }
                for s in self.suggestions
            ],
        }


_LLM_TYPES = frozenset({"llm", "agent", "loop", "parallel"})


def optimize_graph(graph: WorkflowGraph) -> OptimizationReport:
    report = OptimizationReport()
    llm_nodes = [n for n in graph.nodes if n.type in _LLM_TYPES]
    report.estimated_llm_calls = len(llm_nodes)

    # Detect consecutive LLM nodes that could be merged
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        if e.from_id in adj:
            adj[e.from_id].append(e.to_id)
    nmap = graph.node_map()

    for n in graph.nodes:
        if n.type != "llm":
            continue
        children = adj.get(n.id, [])
        for cid in children:
            child = nmap.get(cid)
            if child and child.type == "llm":
                report.suggestions.append(
                    OptimizationSuggestion(
                        "merge_llm_nodes",
                        "latency",
                        f"Consider merging consecutive LLM nodes {n.id} → {cid}",
                        impact="high",
                        node_ids=[n.id, cid],
                    )
                )

    retrieve_nodes = [n for n in graph.nodes if n.type == "retrieve"]
    if len(retrieve_nodes) > 1:
        report.suggestions.append(
            OptimizationSuggestion(
                "batch_retrieval",
                "knowledge",
                "Multiple retrieve nodes — consider single retrieval with higher limit",
                impact="medium",
                node_ids=[n.id for n in retrieve_nodes],
            )
        )

    for n in graph.nodes:
        if n.type == "loop":
            mx = int((n.data or {}).get("max") or 5)
            conc = int((n.data or {}).get("concurrency") or 3)
            if mx > 3 and conc < mx:
                report.suggestions.append(
                    OptimizationSuggestion(
                        "increase_loop_concurrency",
                        "parallel",
                        f"Loop {n.id}: increase concurrency to reduce latency",
                        impact="medium",
                        node_ids=[n.id],
                    )
                )
        if n.type == "parallel":
            branches = (n.data or {}).get("branches") or []
            if len(branches) > 3:
                report.suggestions.append(
                    OptimizationSuggestion(
                        "reduce_parallel_branches",
                        "cost",
                        f"Parallel node {n.id} has {len(branches)} branches — token cost may be high",
                        impact="medium",
                        node_ids=[n.id],
                    )
                )

    if llm_nodes and not retrieve_nodes:
        report.suggestions.append(
            OptimizationSuggestion(
                "add_retrieval",
                "knowledge",
                "No retrieval nodes — consider RAG for grounded answers",
                impact="low",
            )
        )

    # Independent branches at same depth (simplified: nodes with same in-degree 0 besides trigger)
    indegree: dict[str, int] = {n.id: 0 for n in graph.nodes}
    for e in graph.edges:
        if e.to_id in indegree:
            indegree[e.to_id] += 1
    roots = [nid for nid, d in indegree.items() if d == 0]
    if len(roots) > 1:
        report.parallelizable_groups.append(roots)
        report.suggestions.append(
            OptimizationSuggestion(
                "parallel_roots",
                "parallel",
                "Multiple root nodes could execute in parallel",
                impact="medium",
                node_ids=roots,
            )
        )

    report.suggestions.append(
        OptimizationSuggestion(
            "enable_prompt_cache",
            "cache",
            "Enable runtime prompt cache for repeated inputs",
            impact="low",
        )
    )
    return report
