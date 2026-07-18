"""Workflow AI Copilot — generate, fix, explain, optimize workflows."""

from __future__ import annotations

from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.execution import execute_chat_sync
from app.workflow_intelligence.graph.parser import parse_graph
from app.workflow_intelligence.optimizer import optimize_graph
from app.workflow_intelligence.graph.validator import validate_graph


async def copilot_explain(ctx: RuntimeContext, graph_json: str | dict) -> str:
    graph = parse_graph(graph_json)
    validation = validate_graph(graph)
    summary = f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}, Score: {validation.score}"
    system = "Explain this workflow to a non-technical user in 3–5 sentences."
    user = f"{summary}\n\nGraph:\n{graph.to_dict()}"
    return await execute_chat_sync(ctx, system, user[:6000])


async def copilot_fix(ctx: RuntimeContext, graph_json: str | dict, issue: str) -> dict[str, Any]:
    graph = parse_graph(graph_json)
    validation = validate_graph(graph)
    system = (
        "You fix NovaFlow workflow graphs. Output ONLY valid JSON with keys nodes and edges. "
        "Preserve node ids when possible. Fix the reported issue."
    )
    user = f"Issue: {issue}\n\nCurrent graph:\n{graph.to_dict()}\n\nValidation:\n{validation.to_dict()}"
    raw = await execute_chat_sync(ctx, system, user[:8000])
    import re, json

    match = re.search(r"\{[\s\S]*\}", raw or "")
    if match:
        try:
            fixed = json.loads(match.group(0))
            return {"graph": fixed, "explanation": "Graph patched by copilot"}
        except json.JSONDecodeError:
            pass
    return {"graph": graph.to_dict(), "explanation": "Could not auto-fix — review validation issues"}


async def copilot_suggest(ctx: RuntimeContext, graph_json: str | dict) -> dict[str, Any]:
    graph = parse_graph(graph_json)
    opt = optimize_graph(graph)
    return opt.to_dict()


async def copilot_generate_tests(ctx: RuntimeContext, graph_json: str | dict) -> list[dict]:
    graph = parse_graph(graph_json)
    system = (
        "Generate 3 workflow test cases as JSON array: "
        '[{"name","input_text","expected_contains"}]. Output JSON only.'
    )
    raw = await execute_chat_sync(ctx, system, str(graph.to_dict())[:4000])
    import re, json

    match = re.search(r"\[[\s\S]*\]", raw or "")
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return [
        {"name": "happy path", "input_text": "test input", "expected_contains": ""},
    ]
