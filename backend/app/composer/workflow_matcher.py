"""Match user goals to existing workspace workflows via heuristics + optional LLM."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.database import Workflow

MATCH_THRESHOLD = 0.55


def _graph_summary(graph: dict[str, Any]) -> str:
    nodes = graph.get("nodes") or []
    types: list[str] = []
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict):
                types.append(str(n.get("type") or ""))
    elif isinstance(nodes, dict):
        for n in nodes.values():
            if isinstance(n, dict):
                types.append(str(n.get("type") or ""))
    return ", ".join(sorted(set(t for t in types if t)))


def _heuristic_score(goal: str, wf: Workflow, graph: dict[str, Any]) -> float:
    g = (goal or "").lower()
    name = (wf.name or "").lower()
    desc = (wf.desc or "").lower()
    score = 0.0
    if name and name in g:
        score += 0.4
    if desc and any(w in g for w in desc.split()[:8] if len(w) > 4):
        score += 0.15
    types = _graph_summary(graph)
    for token in ("telegram", "jira", "email", "github", "slack", "calendar"):
        if token in g and token in types.lower():
            score += 0.12
    if re.search(r"\bemail\b", g) and "notify" in types and "email" in types:
        score += 0.1
    return min(score, 1.0)


def list_workflow_candidates(db: Session, workspace_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(Workflow)
        .filter(Workflow.workspace_id == workspace_id, Workflow.status != -1)
        .order_by(Workflow.update_time.desc())
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for wf in rows:
        try:
            graph = json.loads(wf.graph_json or "{}")
        except json.JSONDecodeError:
            graph = {}
        out.append(
            {
                "id": wf.id,
                "name": wf.name,
                "desc": wf.desc or "",
                "node_types": _graph_summary(graph),
                "graph": graph,
            }
        )
    return out


def match_workflow(
    db: Session,
    workspace_id: int,
    goal: str,
    requirements: dict[str, Any] | None,
    llm_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return {match_id, match_name, confidence, modify_needed, gaps[], action: create|modify|reuse}.
    """
    candidates = list_workflow_candidates(db, workspace_id)
    if not candidates:
        return {"action": "create", "confidence": 0.0, "gaps": []}

    scored: list[tuple[float, dict[str, Any]]] = []
    for c in candidates:
        wf_row = db.get(Workflow, c["id"])
        if not wf_row:
            continue
        s = _heuristic_score(goal, wf_row, c.get("graph") or {})
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])

    best_score = scored[0][0] if scored else 0.0
    best = scored[0][1] if scored else None

    cfg = dict(llm_cfg or {})
    if cfg.get("api_key") and candidates:
        try:
            from app.services.llm import complete_text

            brief = [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "desc": (c["desc"] or "")[:120],
                    "nodes": c["node_types"],
                }
                for c in candidates[:8]
            ]
            raw = complete_text(
                system=(
                    "Return JSON only: "
                    '{"match_id": "workflow id or null", "confidence": 0-1, '
                    '"modify_needed": bool, "gaps": ["..."], "action": "create|modify|reuse"}'
                ),
                user=f"Goal: {(goal or '')[:800]}\nRequirements: {json.dumps(requirements or {})[:600]}\n"
                f"Workflows: {json.dumps(brief)}",
                cfg=cfg,
                db=db,
            )
            m = re.search(r"\{[\s\S]*\}", raw or "")
            if m:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict) and parsed.get("match_id"):
                    match_id = str(parsed["match_id"])
                    cand = next((c for c in candidates if c["id"] == match_id), None)
                    if cand:
                        return {
                            "action": parsed.get("action") or "modify",
                            "match_id": match_id,
                            "match_name": cand["name"],
                            "confidence": float(parsed.get("confidence") or 0.7),
                            "modify_needed": bool(parsed.get("modify_needed")),
                            "gaps": list(parsed.get("gaps") or []),
                            "graph": cand.get("graph"),
                        }
        except Exception:
            pass

    if best and best_score >= MATCH_THRESHOLD:
        return {
            "action": "modify",
            "match_id": best["id"],
            "match_name": best["name"],
            "confidence": best_score,
            "modify_needed": True,
            "gaps": [],
            "graph": best.get("graph"),
        }
    return {"action": "create", "confidence": best_score, "gaps": []}
