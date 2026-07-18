"""AgentOS reasoning engine — traces, reflection, confidence."""

from __future__ import annotations

import json
from typing import Any


def build_reasoning_trace(
    *,
    goal: str,
    tool_results: list[dict] | None = None,
    plan: dict | None = None,
    reflections: list[str] | None = None,
) -> dict[str, Any]:
    tool_results = tool_results or []
    reflections = reflections or []
    evidence_count = len(tool_results)
    kb_hits = sum(1 for t in tool_results if t.get("tool") == "kb_search")
    return {
        "goal": goal,
        "task_reasoning": f"Decomposed into {len((plan or {}).get('tasks') or [])} tasks",
        "tool_reasoning": f"Executed {evidence_count} tools, {kb_hits} knowledge searches",
        "knowledge_reasoning": "Grounded in KOS when kb_search used" if kb_hits else "No knowledge retrieval",
        "reflections": reflections,
        "steps": [
            {"step": "plan", "detail": (plan or {}).get("goal", goal)},
            {"step": "tools", "detail": [t.get("tool") for t in tool_results]},
            {"step": "synthesize", "detail": "Merged tool evidence into response"},
        ],
    }


def score_confidence(
    *,
    tool_results: list[dict] | None = None,
    verification_verdict: str = "pending",
    output_length: int = 0,
) -> float:
    tool_results = tool_results or []
    score = 0.5
    if tool_results:
        score += min(0.25, len(tool_results) * 0.05)
    if verification_verdict == "pass":
        score += 0.15
    elif verification_verdict == "fail":
        score -= 0.2
    if output_length > 50:
        score += 0.05
    return round(max(0.0, min(1.0, score)), 2)


def self_critique(output: str, tool_results: list[dict] | None = None) -> dict[str, Any]:
    issues = []
    if not output.strip():
        issues.append("Empty output")
    if not tool_results and len(output) > 500:
        issues.append("Long answer without tool evidence")
    if "I don't know" in output.lower() or "uncertain" in output.lower():
        issues.append("Expressed uncertainty — may need more retrieval")
    return {
        "issues": issues,
        "needs_retry": len(issues) > 1,
        "quality": "good" if not issues else "review",
    }
