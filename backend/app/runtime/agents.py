"""Agent runtime — planning, tool invocation, observation, retry, and limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.prompt import PromptInputs, compile_prompt
from app.runtime.tools import execute_tools, format_tools_context
from app.services.agent_tools import DEFAULT_AGENT_SYSTEM


@dataclass
class AgentLimits:
    max_tools: int = 3
    max_steps: int = 1
    timeout_seconds: int = 120


@dataclass
class AgentPlan:
    selected_tools: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


# Multi-agent role templates (coordinator delegates; deterministic, observable)
AGENT_ROLES: dict[str, str] = {
    "planner": "Break the user request into 3–5 concrete steps. Output numbered steps only.",
    "research": "Gather evidence from tool results. Output bullet facts with [n] citations when available.",
    "developer": "Produce implementation guidance or code snippets grounded in tool results.",
    "reviewer": "Review the draft for accuracy, gaps, and risks. Output pass/fail plus fixes.",
    "writer": "Produce the final user-facing answer: lead with conclusion, then supporting bullets.",
    "coordinator": "Merge specialist outputs into one coherent answer. Do not invent new facts.",
}


async def run_agent_loop(
    ctx: RuntimeContext,
    user_input: str,
    tool_ids: list[str],
    *,
    system: str = DEFAULT_AGENT_SYSTEM,
    knowledge_id: int | None = None,
    limits: AgentLimits | None = None,
) -> dict[str, Any]:
    """Deterministic agent loop: select tools → observe → synthesize."""
    from app.runtime.execution import execute_chat_sync
    from app.services.agent_tools import _format_tool_block

    limits = limits or AgentLimits()
    tool_ids = [t for t in (tool_ids or []) if t][:5]
    system = (system or "").strip() or DEFAULT_AGENT_SYSTEM

    if not tool_ids:
        compiled = compile_prompt(
            PromptInputs(system_prompt=system, user_prompt=user_input)
        )
        output = await execute_chat_sync(ctx, compiled.system, compiled.user)
        return {"output": output, "tool_results": [], "tools": [], "selected_tools": []}

    tool_results_raw = await execute_tools(
        ctx, tool_ids, user_input, knowledge_id=knowledge_id, max_tools=limits.max_tools
    )
    selected = [tr.tool_id for tr in tool_results_raw]
    tool_results = [{"tool": tr.tool_id, "result": tr.result[:2000]} for tr in tool_results_raw]
    block = _format_tool_block(tool_results)

    synthesis = compile_prompt(
        PromptInputs(
            system_prompt=system,
            tools_context=format_tools_context(selected),
            user_prompt=(
                f"## User request\n{user_input}\n\n"
                f"## Tool results (selected: {', '.join(selected)})\n{block}\n\n"
                f"## Your job\nSynthesize a final answer for the user. "
                f"Prefer concrete statements grounded in the tool results."
            ),
        )
    )
    output = await execute_chat_sync(ctx, synthesis.system, synthesis.user)
    return {
        "output": output,
        "tool_results": tool_results,
        "tools": tool_ids,
        "selected_tools": selected,
    }


async def run_multi_agent(
    ctx: RuntimeContext,
    user_input: str,
    roles: list[str],
    *,
    tool_ids: list[str] | None = None,
    knowledge_id: int | None = None,
) -> dict[str, Any]:
    """Run specialist roles sequentially; coordinator merges outputs."""
    from app.runtime.execution import execute_chat_sync

    roles = [r for r in roles if r in AGENT_ROLES] or ["writer"]
    if "coordinator" not in roles:
        roles.append("coordinator")

    transcripts: list[str] = []
    tool_payload = {}
    if tool_ids:
        tool_payload = await run_agent_loop(
            ctx, user_input, tool_ids, knowledge_id=knowledge_id
        )
        transcripts.append(f"## Tool evidence\n{tool_payload.get('output', '')}")

    for role in roles:
        if role == "coordinator":
            continue
        prompt = compile_prompt(
            PromptInputs(
                system_prompt=AGENT_ROLES[role],
                conversation_context="\n\n".join(transcripts),
                user_prompt=user_input,
            )
        )
        out = await execute_chat_sync(ctx, prompt.system, prompt.user)
        transcripts.append(f"## {role.title()}\n{out}")

    coord = compile_prompt(
        PromptInputs(
            system_prompt=AGENT_ROLES["coordinator"],
            conversation_context="\n\n".join(transcripts),
            user_prompt=user_input,
        )
    )
    final = await execute_chat_sync(ctx, coord.system, coord.user)
    return {
        "output": final,
        "roles": roles,
        "transcripts": transcripts,
        "tool_results": tool_payload.get("tool_results") or [],
    }
