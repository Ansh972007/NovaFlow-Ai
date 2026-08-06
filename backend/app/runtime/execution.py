"""Execution engine — provider calls through model router."""

from __future__ import annotations

from typing import AsyncIterator

from app.runtime.context import RuntimeContext
from app.runtime.providers import resolve_provider
from app.runtime.router import route_model
from app.services.llm import stream_chat, stream_chat_sync


async def execute_chat_stream(
    ctx: RuntimeContext,
    system: str,
    user: str,
    *,
    history: list[dict] | None = None,
    usage_out: dict | None = None,
    policy: str = "default",
) -> AsyncIterator[str]:
    try:
        provider = resolve_provider(ctx.db)
        decision = route_model(ctx.db, ctx.workspace_id, provider, policy=policy)
        usage = usage_out if usage_out is not None else {}
        usage.setdefault("model", decision.model)
        usage.setdefault("provider_type", decision.provider_type)
        usage.setdefault("routing_policy", decision.policy)
        usage.setdefault("routing_reason", decision.reason)

        async for token in stream_chat(
            system,
            user,
            db=ctx.db,
            workspace_id=ctx.workspace_id,
            cancel_event=ctx.cancel_event,
            usage_out=usage,
            history=history,
        ):
            yield token
    except ValueError as e:
        # Handle missing API key gracefully
        if "No LLM provider configured" in str(e) or "No API key configured" in str(e):
            yield "To use AI features, please add your API key in **Settings → Model providers**. "
            yield "You can use providers like OpenRouter, OpenAI, or others. "
            yield "Each user needs their own API key to build and run workflows."
        else:
            raise


async def execute_chat_sync(
    ctx: RuntimeContext,
    system: str,
    user: str,
    *,
    history: list[dict] | None = None,
    policy: str = "default",
) -> str:
    try:
        provider = resolve_provider(ctx.db)
        decision = route_model(ctx.db, ctx.workspace_id, provider, policy=policy)
        return await stream_chat_sync(
            system,
            user,
            db=ctx.db,
            workspace_id=ctx.workspace_id,
            history=history,
        )
    except ValueError as e:
        if "No LLM provider configured" in str(e) or "No API key configured" in str(e):
            return "To use AI features, please add your API key in **Settings → Model providers**. Each user needs their own API key to build and run workflows."
        else:
            raise
