"""Bridge workflow engine nodes to Enterprise AI Runtime."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.orm import Session

from app.runtime.context import RuntimeContext
from app.runtime.execution import execute_chat_stream, execute_chat_sync
from app.runtime.knowledge import resolve_knowledge_base
from app.runtime.pipeline import AIRuntime, AgentRequest, ChatRequest
from app.runtime.prompt import PromptInputs, compile_prompt
from app.runtime.validation import validate_markdown_output


def make_runtime_ctx(
    db: Session,
    *,
    user_id: int,
    workspace_id: int | None,
    role: str = "editor",
    cancel_event=None,
    trace_id: str = "",
) -> RuntimeContext:
    import uuid

    ctx = RuntimeContext.from_ws(
        db,
        user_id=user_id,
        workspace_id=workspace_id or 0,
        role=role,
        cancel_event=cancel_event,
    )
    if not trace_id:
        trace_id = uuid.uuid4().hex[:16]
    ctx.trace_id = trace_id
    return ctx


async def workflow_retrieve(
    ctx: RuntimeContext,
    knowledge_id: int,
    query: str,
    *,
    limit: int = 5,
) -> tuple[str, int]:
    bundle = resolve_knowledge_base(ctx, knowledge_id, query, limit=limit)
    return bundle.context, bundle.hit_count


async def workflow_llm_sync(
    ctx: RuntimeContext,
    system: str,
    user: str,
    *,
    retrieved: str = "",
) -> str:
    compiled = compile_prompt(
        PromptInputs(
            system_prompt=system,
            knowledge_context=retrieved,
            user_prompt=user,
        )
    )
    runtime = AIRuntime(ctx)
    req = ChatRequest(user_message=compiled.user, system_prompt=compiled.system)
    result = await runtime.chat(req)
    return validate_markdown_output(result.content).content


async def workflow_llm_stream(
    ctx: RuntimeContext,
    system: str,
    user: str,
    *,
    retrieved: str = "",
) -> AsyncIterator[str]:
    compiled = compile_prompt(
        PromptInputs(
            system_prompt=system,
            knowledge_context=retrieved,
            user_prompt=user,
        )
    )
    runtime = AIRuntime(ctx)
    req = ChatRequest(user_message=compiled.user, system_prompt=compiled.system)
    async for token in runtime.chat_stream(req):
        yield token


async def workflow_agent(
    ctx: RuntimeContext,
    user_input: str,
    tools: list[str],
    *,
    system: str = "",
    knowledge_id: int | None = None,
    agent_id: str = "",
) -> dict:
    from app.agent_os.integration import execute_agent_from_runtime

    result = await execute_agent_from_runtime(
        ctx,
        user_input,
        tools=tools,
        system=system,
        knowledge_id=knowledge_id,
        agent_id=agent_id,
    )
    return {
        "output": result.get("output"),
        "tool_results": result.get("tool_results"),
        "selected_tools": result.get("selected_tools"),
        "metrics": result.get("metrics"),
        "run_id": result.get("run_id"),
        "confidence": result.get("confidence"),
    }
