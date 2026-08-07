"""LLM-assisted workflow graph planning — validated DAG within executable palette."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.workflow_intelligence.node_registry import get_allowed_planner_types, planner_type_summary

ALLOWED_NODE_TYPES = get_allowed_planner_types()


def is_llm_graph_compose_enabled(db: Session, workspace_id: int) -> bool:
    """Feature flag via PlatformPolicy — disabled when chat.llm_graph_compose is enforced block."""
    try:
        from app.database import PlatformPolicy

        rows = (
            db.query(PlatformPolicy)
            .filter(
                PlatformPolicy.workspace_id == workspace_id,
                PlatformPolicy.enabled == 1,
                PlatformPolicy.severity == "enforce",
                PlatformPolicy.rule_key == "chat.llm_graph_compose",
            )
            .all()
        )
        for row in rows:
            val = (row.rule_value or "").strip().lower()
            if val in ("block", "deny", "false", "0", "off"):
                return False
    except Exception:
        pass
    return True


def _validate_graph(graph: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not isinstance(nodes, list) or len(nodes) < 2:
        return None, "Graph needs at least two nodes"
    ids: set[str] = set()
    for n in nodes:
        if not isinstance(n, dict):
            return None, "Invalid node entry"
        nid = str(n.get("id") or "").strip()
        ntype = str(n.get("type") or "").strip().lower()
        if not nid or ntype not in ALLOWED_NODE_TYPES:
            return None, f"Invalid node type or id: {ntype}"
        ids.add(nid)
    if not edges:
        return None, "Graph needs edges"
    for e in edges:
        if not isinstance(e, dict):
            return None, "Invalid edge"
        src, tgt = str(e.get("source") or ""), str(e.get("target") or "")
        if src not in ids or tgt not in ids:
            return None, "Edge references missing node"
    return {"nodes": nodes, "edges": edges}, ""


def plan_workflow_graph(
    goal: str,
    requirements: dict[str, Any] | None,
    llm_cfg: dict[str, Any] | None,
    *,
    required_caps: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Best-effort LLM DAG planner. Returns executable graph dict or None (caller falls back).
    Never raises.
    """
    cfg = dict(llm_cfg or {})
    if not cfg.get("api_key"):
        return None
    req = requirements or {}
    caps = ", ".join(required_caps or []) or "cap_workflow"
    sys = (
        "Design a minimal workflow graph as JSON with keys nodes and edges only. "
        f"Allowed node types: {', '.join(sorted(ALLOWED_NODE_TYPES))}. "
        "First node must be type trigger. Last nodes may be output and/or multiple notify nodes. "
        "Do not add notify unless the user asked for delivery (email, telegram reply, slack, etc.). "
        "Each node: id, type, data (label string). Each edge: source, target. "
        f"Required fields per type:\n{planner_type_summary()}\n"
        "Return ONLY JSON object, no markdown."
    )
    user = (
        f"Goal: {(goal or '')[:900]}\n"
        f"Integration: {req.get('integration') or 'general'}\n"
        f"Trigger: {req.get('trigger') or 'manual'}\n"
        f"Output: {req.get('output') or 'workflow'}\n"
        f"Capabilities: {caps}"
    )
    try:
        from app.services.llm import complete_text

        raw = complete_text(system=sys, user=user, cfg=cfg)
        match = re.search(r"\{[\s\S]*\}", raw or "")
        if not match:
            return None
        data = json.loads(match.group(0))
        validated, err = _validate_graph(data)
        if not validated:
            return None
        meta = {
            "planner": "llm_graph",
            "node_types": [n.get("type") for n in validated["nodes"] if isinstance(n, dict)],
        }
        return {
            "nodes": validated["nodes"],
            "edges": validated["edges"],
            "meta": meta,
        }
    except Exception:
        return None
