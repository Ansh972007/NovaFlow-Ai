import json
import re
import time
import asyncio
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy.orm import Session

from app.database import KnowledgeBase, UsageEvent, Workflow, WorkflowPendingRun, WorkflowRun
from app.services.knowledge import search_chunks_semantic
from app.services.llm import stream_chat, stream_chat_sync

EmitFn = Callable[[dict], Awaitable[None]] | None


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
                {"id": "llm", "type": "llm", "x": 320, "y": 140, "data": {"prompt": "Classify this support ticket and draft a helpful reply."}},
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
                {"id": "llm", "type": "llm", "x": 440, "y": 140, "data": {"prompt": "Synthesize a structured research brief."}},
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Brief"}},
            ],
            "edges": [
                {"from": "trigger", "to": "retrieve"},
                {"from": "retrieve", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
    },
    "enrich": {
        "name": "Transform + LLM",
        "desc": "Format input with a template then run LLM",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Raw input"}},
                {"id": "transform", "type": "transform", "x": 240, "y": 140, "data": {"template": "Message:\n{{input}}"}},
                {"id": "llm", "type": "llm", "x": 440, "y": 140, "data": {"prompt": "You are a helpful assistant."}},
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Reply"}},
            ],
            "edges": [
                {"from": "trigger", "to": "transform"},
                {"from": "transform", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
    },
    "agent_loop": {
        "name": "Agent + review",
        "desc": "Tool agent with human review gate",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Task"}},
                {"id": "agent", "type": "agent", "x": 240, "y": 140, "data": {"tools": ["summarize", "kb_search"]}},
                {"id": "human", "type": "human", "x": 440, "y": 140, "data": {"message": "Review output:\n{{output}}", "require_approval": False}},
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Final"}},
            ],
            "edges": [
                {"from": "trigger", "to": "agent"},
                {"from": "agent", "to": "human"},
                {"from": "human", "to": "output"},
            ],
        },
    },
    "batch": {
        "name": "Batch loop",
        "desc": "Process each line of input in parallel tasks",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Lines"}},
                {"id": "loop", "type": "loop", "x": 260, "y": 140, "data": {"max": 5, "prompt": "Process this item briefly: {{item}}"}},
                {"id": "output", "type": "output", "x": 480, "y": 140, "data": {"label": "Results"}},
            ],
            "edges": [{"from": "trigger", "to": "loop"}, {"from": "loop", "to": "output"}],
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
        "webhook_token": getattr(w, "webhook_token", "") or "",
        "is_public": int(getattr(w, "is_public", 0) or 0),
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


def _apply_template(template: str, context: dict) -> str:
    text = template or ""
    for key in ("input", "retrieved", "output", "http", "transform"):
        text = text.replace(f"{{{{{key}}}}}", str(context.get(key) or ""))
    return text


async def _fetch_http(url: str, method: str = "GET", body: str = "") -> str:
    method = (method or "GET").upper()
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if method == "POST":
            resp = await client.post(url, content=body or None)
        else:
            resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return json.dumps(resp.json())[:8000]
        return (resp.text or "")[:8000]


def log_usage(
    db: Session,
    user_id: int,
    event_type: str,
    resource_id: str,
    meta: dict | None = None,
    workspace_id: int | None = None,
):
    db.add(
        UsageEvent(
            user_id=user_id,
            workspace_id=workspace_id,
            event_type=event_type,
            resource_id=resource_id,
            meta=json.dumps(meta or {}),
        )
    )
    db.commit()


async def run_workflow(
    db: Session, workflow: Workflow, user_id: int, user_input: str, workspace_id: int | None = None
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}

    context, steps, pause_node = await _execute_graph(db, user_id, graph, user_input.strip(), workspace_id=workspace_id)
    if pause_node:
        pending = WorkflowPendingRun(
            workflow_id=workflow.id,
            user_id=user_id,
            workspace_id=workspace_id or workflow.workspace_id,
            context_json=json.dumps(context),
            graph_json=json.dumps(graph),
            pause_after_node=pause_node,
            steps_json=json.dumps(steps),
            status=0,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        return {
            "workflow_id": workflow.id,
            "output": context.get("output") or "",
            "steps": steps,
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "pending_run_id": pending.id,
            "status": "pending_human",
        }

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context["input"]

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or workflow.workspace_id,
        input_text=user_input[:4000],
        output_text=final_output[:8000],
        status=1,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    log_usage(db, user_id, "workflow_run", workflow.id, {"duration_ms": duration_ms}, workspace_id or workflow.workspace_id)
    db.commit()

    return {
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }


async def run_workflow_with_progress(
    db: Session,
    workflow: Workflow,
    user_id: int,
    user_input: str,
    emit: EmitFn,
    workspace_id: int | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}

    async def _emit(event: dict):
        if emit:
            await emit(event)

    context, steps, pause_node = await _execute_graph(
        db, user_id, graph, user_input.strip(), emit=_emit, stream_llm=bool(emit), workspace_id=workspace_id
    )

    if pause_node:
        pending = WorkflowPendingRun(
            workflow_id=workflow.id,
            user_id=user_id,
            workspace_id=workspace_id or workflow.workspace_id,
            context_json=json.dumps(context),
            graph_json=json.dumps(graph),
            pause_after_node=pause_node,
            steps_json=json.dumps(steps),
            status=0,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        duration_ms = int((time.perf_counter() - start) * 1000)
        result = {
            "workflow_id": workflow.id,
            "output": context.get("output") or "",
            "steps": steps,
            "duration_ms": duration_ms,
            "pending_run_id": pending.id,
            "status": "pending_human",
        }
        await _emit({"type": "human_review", "pending_run_id": pending.id, "node_id": pause_node})
        await _emit({"type": "complete", **result})
        return result

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context["input"]

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or workflow.workspace_id,
        input_text=user_input[:4000],
        output_text=final_output[:8000],
        status=1,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    log_usage(db, user_id, "workflow_run", workflow.id, {"duration_ms": duration_ms}, workspace_id or workflow.workspace_id)
    db.commit()

    result = {
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }
    await _emit({"type": "complete", **result})
    return result


async def resume_workflow_pending(
    db: Session,
    pending_id: int,
    user_id: int,
    *,
    approved: bool = True,
    note: str = "",
    workspace_id: int | None = None,
    emit: EmitFn = None,
) -> dict[str, Any]:
    pending = db.get(WorkflowPendingRun, pending_id)
    if not pending or pending.user_id != user_id or pending.status != 0:
        return {"status": "error", "message": "Pending run not found"}
    workflow = db.get(Workflow, pending.workflow_id)
    if not workflow:
        return {"status": "error", "message": "Workflow not found"}

    if not approved:
        pending.status = 2
        db.commit()
        return {"status": "rejected", "pending_run_id": pending_id}

    start = time.perf_counter()
    context = json.loads(pending.context_json or "{}")
    if note.strip():
        context["output"] = note.strip()
    graph = json.loads(pending.graph_json or "{}")
    steps = json.loads(pending.steps_json or "[]")

    async def _emit(event: dict):
        if emit:
            await emit(event)

    context, steps, pause_node = await _execute_graph(
        db,
        user_id,
        graph,
        context.get("input") or "",
        emit=_emit,
        stream_llm=bool(emit),
        workspace_id=workspace_id or pending.workspace_id,
        initial_context=context,
        skip_until_after=pending.pause_after_node,
        initial_steps=steps,
    )

    if pause_node:
        pending.context_json = json.dumps(context)
        pending.steps_json = json.dumps(steps)
        pending.pause_after_node = pause_node
        db.commit()
        return {
            "status": "pending_human",
            "pending_run_id": pending.id,
            "steps": steps,
            "output": context.get("output") or "",
        }

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context.get("input") or ""
    pending.status = 1
    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or pending.workspace_id,
        input_text=(context.get("input") or "")[:4000],
        output_text=final_output[:8000],
        status=1,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    db.commit()
    return {
        "status": "completed",
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }


async def _execute_graph(
    db: Session,
    user_id: int,
    graph: dict,
    user_input: str,
    *,
    skip_llm: bool = False,
    stream_llm: bool = False,
    emit: EmitFn = None,
    workspace_id: int | None = None,
    initial_context: dict | None = None,
    skip_until_after: str | None = None,
    initial_steps: list | None = None,
) -> tuple[dict, list[dict], str | None]:
    context = dict(initial_context) if initial_context else {"input": user_input, "retrieved": "", "output": ""}
    if not initial_context:
        context["input"] = user_input
    steps: list[dict] = list(initial_steps or [])
    llm_messages: tuple[str, str] | None = None
    passed_pause = not skip_until_after

    async def _emit(event: dict):
        if emit:
            await emit(event)

    for node in _topo_order(graph):
        if not passed_pause:
            if node.get("id") == skip_until_after:
                passed_pause = True
            continue
        ntype = node.get("type")
        data = node.get("data") or {}
        step = {"node_id": node.get("id"), "type": ntype, "status": "running"}
        await _emit({"type": "step", "phase": "start", "step": {**step}})

        if ntype == "trigger":
            step["output"] = context["input"]
            step["status"] = "ok"
        elif ntype == "retrieve":
            kid = data.get("knowledge_id")
            limit = int(data.get("limit") or 5)
            hits = []
            if kid:
                kb = db.get(KnowledgeBase, kid)
                if kb and (not workspace_id or kb.workspace_id == workspace_id):
                    hits = search_chunks_semantic(db, kid, context["input"], limit)
            parts = []
            for i, hit in enumerate(hits, 1):
                source = hit.get("file_name") or "document"
                text = (hit.get("text") or "")[:1200]
                parts.append(f"[{i}] ({source})\n{text}")
            context["retrieved"] = "\n\n".join(parts)
            step["output"] = context["retrieved"] or "(no matches)"
            step["hits"] = len(hits)
            step["status"] = "ok"
        elif ntype == "transform":
            template = data.get("template") or "{{input}}"
            rendered = _apply_template(template, context)
            context["transform"] = rendered
            context["output"] = rendered
            step["output"] = rendered[:500] + ("…" if len(rendered) > 500 else "")
            step["status"] = "ok"
        elif ntype == "condition":
            keyword = (data.get("keyword") or "").strip()
            haystack = context.get("input") or ""
            matched = bool(keyword and re.search(re.escape(keyword), haystack, re.I))
            branch = data.get("then_text") if matched else data.get("else_text")
            branch = _apply_template(branch or "", context) if branch else haystack
            context["output"] = branch
            step["matched"] = matched
            step["output"] = branch[:500] + ("…" if len(branch) > 500 else "")
            step["status"] = "ok"
        elif ntype == "http":
            url = _apply_template(data.get("url") or "", context).strip()
            method = (data.get("method") or "GET").upper()
            body = _apply_template(data.get("body") or "", context)
            if not url:
                step["output"] = "(no url)"
                step["status"] = "error"
            else:
                try:
                    result = await _fetch_http(url, method, body)
                    context["http"] = result
                    if data.get("set_output", True):
                        context["output"] = result
                    step["output"] = result[:500] + ("…" if len(result) > 500 else "")
                    step["status"] = "ok"
                except Exception as exc:
                    step["output"] = str(exc)[:500]
                    step["status"] = "error"
        elif ntype == "llm":
            prompt = data.get("prompt") or "You are a helpful assistant."
            user_msg = context.get("transform") or context["input"]
            if context["retrieved"]:
                user_msg = (
                    f"Question: {user_msg}\n\n"
                    f"--- Retrieved context ---\n{context['retrieved']}\n--- End context ---"
                )
            llm_messages = (prompt, user_msg)
            if skip_llm:
                step["output"] = "(streaming)"
                step["status"] = "ok"
            elif stream_llm and emit:
                await _emit({"type": "llm_start"})
                reply = ""
                async for token in stream_chat(prompt, user_msg, db=db, workspace_id=workspace_id):
                    reply += token
                    await _emit({"type": "stream", "message": {"content": token}})
                context["output"] = reply
                step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
                step["status"] = "ok"
                await _emit({"type": "llm_end"})
            else:
                reply = await stream_chat_sync(prompt, user_msg, db=db, workspace_id=workspace_id)
                context["output"] = reply
                step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
                step["status"] = "ok"
        elif ntype == "output":
            step["output"] = context["output"] or context["input"]
            step["status"] = "ok"
        elif ntype == "loop":
            sep = data.get("separator") or "\n"
            max_iter = int(data.get("max") or 5)
            items = [x.strip() for x in (context.get("input") or "").split(sep) if x.strip()][:max_iter]
            prompt_tpl = data.get("prompt") or "Process: {{item}}"
            outputs = []
            for item in items:
                msg = prompt_tpl.replace("{{item}}", item)
                reply = await stream_chat_sync(
                    "You are a helpful assistant.",
                    msg,
                    db=db,
                    workspace_id=workspace_id,
                )
                outputs.append(f"• {item}\n{reply}")
            merged = "\n\n".join(outputs) if outputs else context.get("input", "")
            context["output"] = merged
            step["output"] = merged[:500] + ("…" if len(merged) > 500 else "")
            step["iterations"] = len(items)
            step["status"] = "ok"
        elif ntype == "parallel":
            branches = data.get("branches") or ["Summary", "Key points", "Action items"]
            branches = [str(b) for b in branches][:5]
            tasks = [
                stream_chat_sync(
                    f"Complete this subtask: {b}",
                    context.get("input") or "",
                    db=db,
                    workspace_id=workspace_id,
                )
                for b in branches
            ]
            results = await asyncio.gather(*tasks)
            merged = "\n\n".join(f"## {b}\n{r}" for b, r in zip(branches, results))
            context["output"] = merged
            step["output"] = merged[:500] + ("…" if len(merged) > 500 else "")
            step["status"] = "ok"
        elif ntype == "human":
            message = _apply_template(data.get("message") or "Review: {{output}}", context)
            if data.get("require_approval"):
                await _emit({"type": "human_review", "message": message, "node_id": node.get("id")})
                step["output"] = message
                step["status"] = "pending_human"
                steps.append(step)
                await _emit({"type": "step", "phase": "done", "step": step})
                context["human_pending"] = True
                return context, steps, node.get("id")
            context["output"] = context.get("output") or context.get("input") or message
            step["output"] = message[:500]
            step["status"] = "ok"
        elif ntype == "agent":
            from app.services.agent_tools import run_agent

            tools = data.get("tools") or ["summarize"]
            kid = data.get("knowledge_id")
            reply = await run_agent(
                db,
                context.get("input") or "",
                tools if isinstance(tools, list) else [tools],
                knowledge_id=kid,
                workspace_id=workspace_id,
                system=data.get("prompt") or "You are a capable agent.",
            )
            context["output"] = reply
            step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
            step["status"] = "ok"
        elif ntype == "subgraph":
            sub_id = data.get("workflow_id")
            sub = db.get(Workflow, sub_id) if sub_id else None
            if not sub or (workspace_id and sub.workspace_id != workspace_id):
                step["output"] = "(subgraph not found)"
                step["status"] = "error"
            else:
                try:
                    sub_graph = json.loads(sub.graph_json or "{}")
                except json.JSONDecodeError:
                    sub_graph = {"nodes": [], "edges": []}
                sub_ctx, sub_steps, _ = await _execute_graph(
                    db,
                    user_id,
                    sub_graph,
                    context.get("input") or "",
                    workspace_id=workspace_id,
                )
                context["output"] = sub_ctx.get("output") or ""
                step["output"] = (context["output"] or "")[:500]
                step["sub_steps"] = len(sub_steps)
                step["status"] = "ok"
        else:
            step["status"] = "skipped"

        steps.append(step)
        await _emit({"type": "step", "phase": "done", "step": step})

    if skip_llm and llm_messages:
        context["_llm_system"] = llm_messages[0]
        context["_llm_user"] = llm_messages[1]

    return context, steps, None


async def resolve_workflow_llm_messages(
    db: Session, workflow: Workflow, user_id: int, user_input: str
) -> tuple[str, str]:
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    context, _, _ = await _execute_graph(db, user_id, graph, user_input.strip(), skip_llm=True)
    system = context.get("_llm_system") or "You are a helpful assistant."
    user_msg = context.get("_llm_user") or user_input.strip()
    return system, user_msg
