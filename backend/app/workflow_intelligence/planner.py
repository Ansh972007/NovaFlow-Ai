"""Workflow planner — natural language to execution graph."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.execution import execute_chat_sync
from app.security.rbac import Permission


@dataclass
class WorkflowPlan:
    summary: str = ""
    trigger: str = "trigger"
    suggested_nodes: list[dict] = field(default_factory=list)
    suggested_edges: list[dict] = field(default_factory=list)
    graph: dict = field(default_factory=dict)
    documentation: str = ""
    security_notes: list[str] = field(default_factory=list)
    retry_policy: str = "exponential_backoff"
    permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "trigger": self.trigger,
            "graph": self.graph,
            "documentation": self.documentation,
            "security_notes": self.security_notes,
            "retry_policy": self.retry_policy,
            "permissions": self.permissions,
            "suggested_nodes": self.suggested_nodes,
            "suggested_edges": self.suggested_edges,
        }


def _heuristic_plan(description: str) -> WorkflowPlan:
    """Deterministic fallback when LLM unavailable."""
    desc = description.lower()
    nodes = [
        {"id": "trigger", "type": "trigger", "x": 60, "y": 140, "data": {"label": "Input"}},
    ]
    edges: list[dict] = []
    prev = "trigger"

    if any(w in desc for w in ("invoice", "document", "upload", "extract", "pdf")):
        nodes.append({"id": "retrieve", "type": "retrieve", "x": 260, "y": 140, "data": {"knowledge_id": None, "limit": 6}})
        edges.append({"from": prev, "to": "retrieve"})
        prev = "retrieve"

    nodes.append(
        {
            "id": "llm",
            "type": "llm",
            "x": 460,
            "y": 140,
            "data": {
                "prompt": (
                    "Process the input according to the automation goal. "
                    "Structure output clearly with sections and bullet points."
                )
            },
        }
    )
    edges.append({"from": prev, "to": "llm"})
    prev = "llm"

    if any(w in desc for w in ("notify", "finance", "email", "slack", "alert")):
        nodes.append(
            {"id": "notify", "type": "notify", "x": 660, "y": 140, "data": {"channel": "telegram", "message": "{{output}}"}}
        )
        edges.append({"from": prev, "to": "notify"})
        prev = "notify"

    if any(w in desc for w in ("crm", "jira", "ticket", "issue")):
        nodes.append(
            {"id": "jira", "type": "jira", "x": 860, "y": 140, "data": {"action": "create", "summary": "{{output}}"}}
        )
        edges.append({"from": prev, "to": "jira"})
        prev = "jira"

    if any(w in desc for w in ("http", "api", "webhook", "store")):
        nodes.append(
            {"id": "http", "type": "http", "x": 860, "y": 240, "data": {"method": "POST", "url": "", "body": "{{output}}"}}
        )
        edges.append({"from": prev, "to": "http"})
        prev = "http"

    nodes.append({"id": "output", "type": "output", "x": 1060, "y": 140, "data": {"label": "Result"}})
    edges.append({"from": prev, "to": "output"})

    perms = ["workflow.run"]
    if "retrieve" in [n["id"] for n in nodes]:
        perms.append("knowledge.read")
    if "jira" in [n["id"] for n in nodes]:
        perms.append("integrations.write")

    return WorkflowPlan(
        summary=description[:200],
        graph={"nodes": nodes, "edges": edges},
        suggested_nodes=nodes,
        suggested_edges=edges,
        documentation=f"Automation: {description}",
        security_notes=["Validate HTTP URLs before production", "Scope knowledge bases to workspace"],
        permissions=perms,
    )


async def plan_workflow_from_text(ctx: RuntimeContext, description: str) -> WorkflowPlan:
    """Generate workflow plan from natural language via AI Runtime."""
    description = (description or "").strip()
    if not description:
        return WorkflowPlan(summary="(empty)", graph={"nodes": [], "edges": []})

    ctx.require_permission(Permission.WORKFLOW_WRITE)

    system = (
        "You are a NovaFlow workflow architect. Given an automation description, output ONLY valid JSON:\n"
        "{\n"
        '  "summary": "one line",\n'
        '  "nodes": [{"id","type","x","y","data"}],\n'
        '  "edges": [{"from","to"}],\n'
        '  "documentation": "markdown",\n'
        '  "security_notes": ["..."],\n'
        '  "permissions": ["workflow.run", ...]\n'
        "}\n"
        "Use node types: trigger, retrieve, llm, transform, condition, http, notify, jira, github, agent, output, human.\n"
        "Always include trigger and output nodes. Position x incrementally by 200."
    )
    try:
        raw = await execute_chat_sync(ctx, system, f"Automation request:\n{description[:4000]}")
        match = re.search(r"\{[\s\S]*\}", raw or "")
        if match:
            data = json.loads(match.group(0))
            nodes = data.get("nodes") or []
            edges = data.get("edges") or []
            if nodes:
                return WorkflowPlan(
                    summary=data.get("summary") or description[:200],
                    graph={"nodes": nodes, "edges": edges},
                    suggested_nodes=nodes,
                    suggested_edges=edges,
                    documentation=data.get("documentation") or "",
                    security_notes=data.get("security_notes") or [],
                    permissions=data.get("permissions") or ["workflow.run"],
                )
    except Exception:
        pass

    plan = _heuristic_plan(description)
    ctx.audit("workflow.plan.generated", detail={"summary": plan.summary[:120]})
    return plan
