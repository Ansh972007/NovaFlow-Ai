"""Assemble real multi-node executable workflow graphs from AIOS solutions."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.composer.recipes import RECIPES, match_recipe
from app.database import ProjectGraph, SolutionGraph, Workflow


def _required_caps_from_solution(graph_payload: dict) -> list[str]:
    required = graph_payload.get("required_capabilities") or []
    if isinstance(required, list):
        return [str(x) for x in required]
    return []


def _goal_text(db: Session, solution: SolutionGraph) -> str:
    project = db.query(ProjectGraph).filter(ProjectGraph.id == solution.project_id).first()
    return (project.business_goal or "").strip() if project else ""


def build_executable_graph(
    *,
    required_caps: list[str],
    goal: str = "",
    knowledge_id: int | None = None,
    recipe_id: str | None = None,
) -> dict[str, Any]:
    """
    Build a runnable workflow graph (nodes/edges) from capability ids + goal hints.
    Used for plan preview, sandbox trial, and deploy.
    """
    caps = set(required_caps or [])
    goal_l = (goal or "").lower()
    recipe = None
    if recipe_id:
        recipe = next((r for r in RECIPES if r["id"] == recipe_id), None)
    if not recipe:
        recipe = match_recipe(goal, fallback_generic=True)
    # Guarantee at least a runnable workflow skeleton
    if not caps:
        caps = set((recipe or {}).get("caps") or ["cap_workflow"])
        if not caps:
            caps = {"cap_workflow"}
    required_caps = list(dict.fromkeys(list(required_caps or []) + list(caps)))
    caps = set(required_caps)

    include_knowledge = bool(knowledge_id) or ("cap_knowledge" in caps) or any(
        k in goal_l for k in ("knowledge", "docs", "rag", "document")
    )
    wants_transform = (
        "csv" in goal_l
        or "etl" in goal_l
        or "transform" in goal_l
        or (recipe and recipe.get("id") == "csv_etl")
    )
    wants_http = (
        "cap_http" in caps
        or "http" in goal_l
        or "webhook" in goal_l
        or (recipe and recipe.get("id") == "webhook_http")
    )
    wants_agent = (
        "cap_agent" in caps
        or "agent" in goal_l
        or "multi-agent" in goal_l
        or "supervisor" in goal_l
        or (recipe and recipe.get("id") == "multi_agent")
    )
    wants_human = any(
        p in goal_l for p in ("ask me first", "human approval", "approve before", "hitl", "ask me before")
    )
    schedule_hint = ""
    if any(k in goal_l for k in ("schedule", "cron", "daily", "weekly", "every day")):
        schedule_hint = "Configure cadence in Schedules after deploy."

    llm_prompt = (
        "You are NovaFlow Composer runtime. "
        "Use retrieved context when available. "
        f"User goal: {goal or '(see input)'}\n"
        "Produce a clear operational deliverable. "
        "If credentials or data are missing, state what is missing."
    )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    x = 60

    def add(node: dict[str, Any]) -> str:
        nonlocal x
        node = {**node, "x": node.get("x", x), "y": node.get("y", 140)}
        nodes.append(node)
        x += 200
        return node["id"]

    trigger_label = "Start / Goal"
    if schedule_hint:
        trigger_label = "Scheduled start"
    prev = add({"id": "trigger", "type": "trigger", "data": {"label": trigger_label, "schedule_note": schedule_hint}})

    if wants_transform:
        nid = add(
            {
                "id": "transform",
                "type": "transform",
                "data": {"expression": "normalize_rows", "input": "{{input}}"},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    if include_knowledge:
        nid = add(
            {
                "id": "retrieve",
                "type": "retrieve",
                "data": {"knowledge_id": knowledge_id, "limit": 6},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    if wants_agent and not wants_transform:
        nid = add(
            {
                "id": "agent",
                "type": "agent",
                "data": {"goal": goal or "{{input}}", "tools": ["summarize", "kb_search"]},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid
    else:
        llm_id = add({"id": "llm", "type": "llm", "data": {"prompt": llm_prompt}})
        edges.append({"from": prev, "to": llm_id})
        prev = llm_id
        if wants_agent:
            nid = add(
                {
                    "id": "agent",
                    "type": "agent",
                    "data": {"goal": goal or "{{input}}", "tools": ["summarize", "kb_search"]},
                }
            )
            edges.append({"from": prev, "to": nid})
            prev = nid

    if "cap_github" in caps or "github" in goal_l:
        nid = add(
            {
                "id": "github",
                "type": "github",
                "data": {
                    "action": "create_issue",
                    "title": "{{output}}",
                    "body": "{{input}}",
                },
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    if "cap_jira" in caps or "jira" in goal_l:
        nid = add(
            {
                "id": "jira",
                "type": "jira",
                "data": {
                    "action": "create",
                    "project_key": "OPS",
                    "summary": "{{output}}",
                    "description": "{{input}}",
                },
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    if "cap_linear" in caps or "linear" in goal_l:
        nid = add(
            {
                "id": "linear",
                "type": "linear",
                "data": {"title": "{{output}}", "description": "{{input}}"},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    wants_notify = any(
        c in caps
        for c in ("cap_telegram", "cap_slack", "cap_discord", "cap_smtp", "cap_whatsapp", "cap_outlook")
    ) or any(
        k in goal_l
        for k in ("telegram", "slack", "discord", "email", "digest", "notify", "bot", "whatsapp", "outlook")
    )

    if wants_human and (wants_notify or wants_http or "cap_github" in caps):
        nid = add(
            {
                "id": "human",
                "type": "human",
                "data": {"prompt": "Review this output before the next side-effect.", "timeout_minutes": 60},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    if wants_notify:
        channel = "telegram"
        to_addr = "{{chat_id}}"
        if "cap_outlook" in caps or "outlook" in goal_l or "microsoft 365" in goal_l:
            channel = "email"
            to_addr = "{{email}}"
        elif "cap_smtp" in caps or "email" in goal_l or "digest" in goal_l or "mail" in goal_l or "gmail" in goal_l:
            channel = "email"
            to_addr = "{{email}}"
        elif "cap_whatsapp" in caps or "whatsapp" in goal_l:
            channel = "whatsapp"
            to_addr = "{{phone}}"
        elif "cap_slack" in caps or "slack" in goal_l:
            channel = "slack"
            to_addr = ""
        elif "cap_discord" in caps or "discord" in goal_l:
            channel = "discord"
            to_addr = ""
        nid = add(
            {
                "id": "notify",
                "type": "notify",
                "data": {
                    "channel": channel,
                    "to": to_addr,
                    "subject": "NovaFlow — {{subject}}",
                    "message": "{{output}}",
                    "credential_id": "",
                },
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    # Commerce / Google / YouTube API connectors
    for cap_id, node_id, url, method, keys in (
        ("cap_shopify", "shopify", "https://{{shop}}/admin/api/2024-01/graphql.json", "POST", ("shopify",)),
        ("cap_google", "google_api", "https://www.googleapis.com/", "GET", ("google",)),
        ("cap_youtube", "youtube", "https://www.googleapis.com/youtube/v3/search", "GET", ("youtube",)),
    ):
        if cap_id in caps or any(k in goal_l for k in keys):
            if not any(n.get("id") == node_id for n in nodes):
                nid = add(
                    {
                        "id": node_id,
                        "type": "http",
                        "data": {
                            "url": url,
                            "method": method,
                            "body": "{{output}}",
                            "auth": cap_id.replace("cap_", ""),
                        },
                    }
                )
                edges.append({"from": prev, "to": nid})
                prev = nid

    if wants_http:
        # Prefer custom SaaS base_url when detected; else webhook placeholder
        http_url = "{{webhook_url}}"
        if any(
            k in goal_l
            for k in (
                "hubspot",
                "stripe",
                "notion",
                "salesforce",
                "airtable",
                "zendesk",
                "custom api",
                "base_url",
            )
        ):
            http_url = "{{base_url}}"
        nid = add(
            {
                "id": "http",
                "type": "http",
                "data": {"url": http_url, "method": "POST", "body": "{{output}}", "auth": "custom"},
            }
        )
        edges.append({"from": prev, "to": nid})
        prev = nid

    out_id = add({"id": "output", "type": "output", "data": {"label": "Result"}})
    edges.append({"from": prev, "to": out_id})

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "required_capabilities": list(required_caps or []),
            "include_knowledge": include_knowledge,
            "node_types": [n["type"] for n in nodes],
            "recipe_id": (recipe or {}).get("id"),
            "recipe_name": (recipe or {}).get("name"),
            "schedule_note": schedule_hint or None,
        },
    }


def heal_executable_graph(
    graph: dict[str, Any],
    *,
    knowledge_id: int | None = None,
    drop_notify_without_creds: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Rule-based repairs for sandbox/deploy graphs. Returns (graph, fixes)."""
    fixes: list[str] = []
    nodes = list((graph or {}).get("nodes") or [])
    edges = list((graph or {}).get("edges") or [])
    if not isinstance(nodes, list):
        return graph, fixes

    types = {str(n.get("type")) for n in nodes if isinstance(n, dict)}
    ids = {str(n.get("id")) for n in nodes if isinstance(n, dict) and n.get("id")}

    if "output" not in types:
        oid = "output"
        nodes.append({"id": oid, "type": "output", "data": {"label": "Result"}, "x": 900, "y": 140})
        # connect last non-output node
        last = None
        for n in nodes:
            if isinstance(n, dict) and n.get("type") != "output":
                last = n.get("id")
        if last:
            edges.append({"from": last, "to": oid})
        fixes.append("Added missing output node")

    if knowledge_id is not None:
        for n in nodes:
            if isinstance(n, dict) and n.get("type") == "retrieve":
                data = dict(n.get("data") or {})
                if data.get("knowledge_id") != knowledge_id:
                    data["knowledge_id"] = knowledge_id
                    n["data"] = data
                    fixes.append("Rebound retrieve.knowledge_id")

    if drop_notify_without_creds:
        drop_ids = {n["id"] for n in nodes if isinstance(n, dict) and n.get("type") == "notify"}
        if drop_ids:
            nodes = [n for n in nodes if not (isinstance(n, dict) and n.get("id") in drop_ids)]
            edges = [
                e
                for e in edges
                if not (
                    isinstance(e, dict)
                    and (e.get("from") in drop_ids or e.get("to") in drop_ids)
                )
            ]
            # reconnect orphaned paths to output
            out = next((n.get("id") for n in nodes if isinstance(n, dict) and n.get("type") == "output"), None)
            srcs = {e.get("from") for e in edges if isinstance(e, dict)}
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                nid = n.get("id")
                if nid and n.get("type") not in ("output", "trigger") and nid not in srcs and out:
                    edges.append({"from": nid, "to": out})
            fixes.append("Removed notify nodes pending credentials")

    # Ensure every node id referenced by edges exists
    ids = {str(n.get("id")) for n in nodes if isinstance(n, dict) and n.get("id")}
    edges = [
        e
        for e in edges
        if isinstance(e, dict) and e.get("from") in ids and e.get("to") in ids
    ]

    meta = dict((graph or {}).get("meta") or {})
    meta["node_types"] = [n.get("type") for n in nodes if isinstance(n, dict)]
    meta["healed"] = True
    meta["heal_fixes"] = fixes
    return {"nodes": nodes, "edges": edges, "meta": meta}, fixes


def preview_graph_for_solution(
    db: Session,
    solution_id: str,
    *,
    knowledge_id: int | None = None,
) -> dict[str, Any]:
    solution = db.query(SolutionGraph).filter(SolutionGraph.id == solution_id).first()
    if not solution:
        raise ValueError("Solution graph not found.")
    payload = json.loads(solution.graph_payload or "{}")
    caps = _required_caps_from_solution(payload)
    goal = _goal_text(db, solution)
    recipe_id = (payload.get("recipe") or {}).get("id") if isinstance(payload.get("recipe"), dict) else None
    return build_executable_graph(
        required_caps=caps, goal=goal, knowledge_id=knowledge_id, recipe_id=recipe_id
    )


def assemble_executable_workflow(
    db: Session,
    workspace_id: int,
    user_id: int,
    solution_id: str,
    *,
    knowledge_id: int | None = None,
) -> Workflow:
    """Persist a runnable Workflow from a SolutionGraph."""
    solution = db.query(SolutionGraph).filter(SolutionGraph.id == solution_id).first()
    if not solution:
        raise ValueError("Solution graph not found.")

    graph_json = preview_graph_for_solution(db, solution_id, knowledge_id=knowledge_id)

    workflow = Workflow(
        name=f"AIOS Workflow {solution_id[:8]}",
        desc="Executable graph compiled from AIOS SolutionGraph",
        graph_json=json.dumps({"nodes": graph_json["nodes"], "edges": graph_json["edges"]}),
        user_id=user_id,
        workspace_id=workspace_id,
        status=1,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow
