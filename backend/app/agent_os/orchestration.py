"""AgentOS multi-agent orchestration."""

from __future__ import annotations

from typing import Any

from app.agent_os.registry import get_type_defaults
from app.runtime.agents import AGENT_ROLES, run_multi_agent
from app.runtime.context import RuntimeContext


async def run_team(
    ctx: RuntimeContext,
    user_input: str,
    *,
    mode: str = "sequential",
    roles: list[str] | None = None,
    tool_ids: list[str] | None = None,
    knowledge_id: int | None = None,
    agent_type: str = "research",
) -> dict[str, Any]:
    """Execute multi-agent team — sequential by default."""
    defaults = get_type_defaults(agent_type)
    roles = roles or defaults.get("roles") or ["writer", "coordinator"]
    tool_ids = tool_ids or defaults.get("default_tools") or ["summarize"]

    if mode == "parallel":
        # Parallel: run tool phase once, then fan-out role prompts (simulated via multi-agent)
        result = await run_multi_agent(ctx, user_input, roles, tool_ids=tool_ids, knowledge_id=knowledge_id)
        result["mode"] = "parallel"
        return result

    result = await run_multi_agent(ctx, user_input, roles, tool_ids=tool_ids, knowledge_id=knowledge_id)
    result["mode"] = "sequential"
    return result


async def run_consensus(
    ctx: RuntimeContext,
    user_input: str,
    *,
    voters: list[str] | None = None,
    tool_ids: list[str] | None = None,
    knowledge_id: int | None = None,
) -> dict[str, Any]:
    """Run multiple reviewer roles and pick coordinator merge."""
    voters = voters or ["reviewer", "research", "writer"]
    voters = [v for v in voters if v in AGENT_ROLES] or ["reviewer", "writer"]
    result = await run_multi_agent(ctx, user_input, voters + ["coordinator"], tool_ids=tool_ids, knowledge_id=knowledge_id)
    result["mode"] = "consensus"
    return result
