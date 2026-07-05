import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, UsageEvent, Workflow, WorkflowRun
from app.services.knowledge import search_chunks_semantic
from app.services.llm import stream_chat_sync


FLOW_TYPE_WORKFLOW = 10

DEFAULT_RAG_GRAPH = {
    "nodes": [
        {"id": "trigger", "type": "trigger", "x": 60, "y": 140, "data": {"label": "User input"}},
        {"id": "retrieve", "type": "retrieve", "x": 260, "y": 140, "data": {"knowledge_id": None, "limit": 5}},
        {"id": "llm", "type": "llm", "x": 460, "y": 140, "data": {"prompt": "Answer using retrieved context. Be concise and cite sources when possible."}},
        {"id": "output", "type": "output", "x": 660, "y": 140, "data": {"label": "Response"}},
    ],
    "edges": [
        {"from": "trigger", "to": "retrieve"},
        {"from": "retrieve", "to": "llm"},
        {"from": "llm", "to": "output"},
    ],
}

TEMPLATES = {
    "rag": {"name": "RAG Q&A pipeline", "desc": "Retrieve docs then answer with LLM", "graph": DEFAULT_RAG_GRAPH},
    "support": {
        "name": "Support triage",
        "desc": "Classify and draft support replies",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 60, "y": 140, "data": {"label": "Ticket"}},
                {"id": "llm", "type": "llm", "x": 320, "y": 140, "data": {"prompt": "Classify this support ticket (billing/technical/account) and draft a helpful reply."}},
                {"id": "output", "type": "output", "x": 580, "y": 140, "data": {"label": "Draft"}},
            ],
            "edges": [{"from": "trigger", "to": "llm"}, {"from": "llm", "to": "output"}],
        },
    },
    "research": {
        "name": "Research brief",
        "desc": "Retrieve sources and synthesize a brief",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Topic"}},
                {"id": "retrieve", "type": "retrieve", "x": 240, "y": 140, "data": {"knowledge_id": None, "limit": 8}},
                {"id": "llm", "type": "llm", "x": 440, "y": 140, "data": {"prompt": "Synthesize a structured research brief with bullet points and key takeaways."}},
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Brief"}},
            ],
            "edges": [
                {"from": "trigger", "to": "retrieve"},
                {"from": "retrieve", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
    },
}


def workflow_dict(w: Workflow) -> dict:
    try:
        graph = json.loads(w.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    return {
        "id": w.id,
        "name": w.name,
        "desc": w.desc or "",
        "description": w.desc or "",
        "status": w.status,
        "flow_type": FLOW_TYPE_WORKFLOW,
        "graph": graph,
        "user_id": w.user_id,
        "write": True,
        "create_time": w.create_time.isoformat() if w.create_time else None,
        "update_time": w.update_time.isoformat() if w.update_time else None,
    }


def _node_map(graph: dict) -> dict[str, dict]:
    return {n["id"]: n for n in graph.get("nodes", []) if n.get("id")}


def _next_nodes(graph: dict, node_id: str) -> list[str]:
    return [e["to"] for e in graph.get("edges", []) if e.get("from") == node_id]


def _topo_order(graph: dict) -> list[dict]:
    nodes = graph.get("nodes", [])
    if not nodes:
        return []
    edges = graph.get("edges", [])
    incoming = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e.get("to") in incoming:
            incoming[e["to"]] += 1
    queue = [nid for nid, c in incoming.items() if c == 0]
    order = []
    nmap = _node_map(graph)
    while queue:
        nid = queue.pop(0)
        if nid in nmap:
            order.append(nmap[nid])
        for e in edges:
            if e.get("from") == nid:
                incoming[e["to"]] -= 1
                if incoming[e["to"]] == 0:
                    queue.append(e["to"])
    if len(order) < len(nodes):
        order = nodes
    return order


def log_usage(db: Session, user_id: int, event_type: str, resource_id: str, meta: dict | None = None):
    db.add(
        UsageEvent(
            user_id=user_id,
            event_type=event_type,
            resource_id=resource_id,
            meta=json.dumps(meta or {}),
        )
    )
    db.commit()


async def run_workflow(db: Session, workflow: Workflow, user_id: int, user_input: str) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}

    context = {"input": user_input.strip(), "retrieved": "", "output": ""}
    steps: list[dict] = []

    for node in _topo_order(graph):
        ntype = node.get("type")
        data = node.get("data") or {}
        step = {"node_id": node.get("id"), "type": ntype, "status": "ok"}

        if ntype == "trigger":
            step["output"] = context["input"]
        elif ntype == "retrieve":
            kid = data.get("knowledge_id")
            limit = int(data.get("limit") or 5)
            hits = []
            if kid:
                kb = db.get(KnowledgeBase, kid)
                if kb and kb.user_id == user_id:
                    hits = search_chunks_semantic(db, kid, context["input"], limit)
            parts = []
            for i, hit in enumerate(hits, 1):
                source = hit.get("file_name") or "document"
                text = (hit.get("text") or "")[:1200]
                parts.append(f"[{i}] ({source})\n{text}")
            context["retrieved"] = "\n\n".join(parts)
            step["output"] = context["retrieved"] or "(no matches)"
            step["hits"] = len(hits)
        elif ntype == "llm":
            prompt = data.get("prompt") or "You are a helpful assistant."
            user_msg = context["input"]
            if context["retrieved"]:
                user_msg = (
                    f"Question: {context['input']}\n\n"
                    f"--- Retrieved context ---\n{context['retrieved']}\n--- End context ---"
                )
            reply = await stream_chat_sync(prompt, user_msg)
            context["output"] = reply
            step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
        elif ntype == "output":
            step["output"] = context["output"] or context["input"]
        else:
            step["status"] = "skipped"

        steps.append(step)

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context["input"]

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        input_text=user_input[:4000],
        output_text=final_output[:8000],
        status=1,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    log_usage(db, user_id, "workflow_run", workflow.id, {"duration_ms": duration_ms})
    db.commit()

    return {
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }
