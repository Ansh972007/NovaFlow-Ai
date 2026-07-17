"""Tool runtime — unified execution for builtin and custom tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.context import RuntimeContext
from app.services.agent_tools import BUILTIN_TOOLS, list_builtin_tools


@dataclass
class ToolResult:
    tool_id: str
    result: str
    ok: bool = True
    meta: dict = field(default_factory=dict)


@dataclass
class ToolSpec:
    tool_id: str
    description: str


def list_tools() -> list[ToolSpec]:
    return [ToolSpec(t["id"], t["description"]) for t in list_builtin_tools()]


def format_tools_context(tool_ids: list[str]) -> str:
    lines = []
    for tid in tool_ids:
        desc = BUILTIN_TOOLS.get(tid, "")
        if desc:
            lines.append(f"- {tid}: {desc}")
    return "\n".join(lines)


async def execute_tool(
    ctx: RuntimeContext,
    tool_id: str,
    user_input: str,
    *,
    knowledge_id: int | None = None,
) -> ToolResult:
    """Run a single tool through the common runtime (permissions + tenant scope)."""
    from app.services.agent_tools import _run_tool

    if tool_id not in BUILTIN_TOOLS:
        return ToolResult(tool_id=tool_id, result=f"Unknown tool: {tool_id}", ok=False)

    if tool_id == "kb_search":
        from app.security.rbac import Permission

        ctx.require_permission(Permission.KNOWLEDGE_READ)

    try:
        result = await _run_tool(
            ctx.db,
            tool_id,
            user_input,
            knowledge_id=knowledge_id,
            workspace_id=ctx.workspace_id,
        )
        return ToolResult(tool_id=tool_id, result=(result or "")[:4000], ok=True)
    except Exception as exc:
        return ToolResult(tool_id=tool_id, result=str(exc), ok=False)


async def execute_tools(
    ctx: RuntimeContext,
    tool_ids: list[str],
    user_input: str,
    *,
    knowledge_id: int | None = None,
    max_tools: int = 3,
) -> list[ToolResult]:
    """Select and run relevant tools (delegates selection to agent_tools heuristics)."""
    from app.services.agent_tools import _followup_input, _select_tools, _TOOL_ORDER

    ids = [t for t in (tool_ids or []) if t in BUILTIN_TOOLS][:5]
    if not ids:
        return []
    selected = _select_tools(user_input, ids, max_tools=min(max_tools, len(ids)))
    selected = sorted(selected, key=lambda t: _TOOL_ORDER.get(t, 5))

    results: list[ToolResult] = []
    prior: list[dict[str, Any]] = []
    for tid in selected:
        arg = _followup_input(tid, user_input, prior)
        tr = await execute_tool(ctx, tid, arg, knowledge_id=knowledge_id)
        results.append(tr)
        prior.append({"tool": tid, "result": tr.result})
    return results
