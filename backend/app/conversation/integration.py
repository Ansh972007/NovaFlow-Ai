"""Conversation persistence hook for chat/agent/workflow paths."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.conversation.service import append_message, get_or_create_for_resource, messages_as_history, get_messages
from app.services.receipt import estimate_cost_usd


def persist_chat_turn(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    organization_id: int | None,
    assistant_id: str,
    user_message: str,
    assistant_message: str,
    conversation_id: str | None = None,
    usage: dict | None = None,
    rag_hits: list | None = None,
    trace_id: str = "",
    event_type: str = "assistant",
) -> dict[str, Any]:
    conv = get_or_create_for_resource(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        organization_id=organization_id,
        conversation_type=event_type if event_type != "chat" else "assistant",
        resource_id=assistant_id,
        conversation_id=conversation_id,
    )
    append_message(
        db,
        conv,
        content=user_message,
        message_type="user",
        role="user",
        created_by=user_id,
        assistant_id=assistant_id,
        trace_id=trace_id,
    )
    usage = usage or {}
    model = usage.get("model") or usage.get("ab_model") or ""
    cost = estimate_cost_usd(model, usage.get("prompt_tokens"), usage.get("completion_tokens"))
    citations = []
    if rag_hits:
        for i, h in enumerate(rag_hits[:8], 1):
            citations.append({"n": i, "file_name": h.get("file_name"), "text": (h.get("text") or "")[:200]})

    append_message(
        db,
        conv,
        content=assistant_message,
        message_type="assistant",
        role="assistant",
        created_by=user_id,
        assistant_id=assistant_id,
        model=model,
        provider=usage.get("provider_type") or "",
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        latency_ms=int(usage.get("latency_ms") or 0) or None,
        cost_usd=cost,
        trace_id=trace_id,
        knowledge_refs=rag_hits or [],
        citations=citations,
        meta={"event_type": event_type, "usage": usage},
    )

    try:
        from app.platform_intelligence.events.emitter import emit_platform_event

        emit_platform_event(
            db,
            "ConversationMessageCreated",
            workspace_id=workspace_id,
            organization_id=organization_id,
            actor_user_id=user_id,
            resource_type="conversation",
            resource_id=conv.id,
            payload={"assistant_id": assistant_id, "trace_id": trace_id},
        )
    except Exception:
        pass

    return {"conversation_id": conv.id}


def persist_agent_turn(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    organization_id: int | None,
    agent_id: str,
    user_input: str,
    output: str,
    conversation_id: str | None = None,
    tool_results: list | None = None,
    selected_tools: list | None = None,
    metrics: dict | None = None,
    knowledge_id: str | None = None,
    trace_id: str = "",
) -> dict[str, Any]:
    conv = get_or_create_for_resource(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        organization_id=organization_id,
        conversation_type="agent",
        resource_id=agent_id or "default-agent",
        conversation_id=conversation_id,
    )
    append_message(
        db,
        conv,
        content=user_input,
        message_type="user",
        role="user",
        created_by=user_id,
        agent_ref=agent_id,
        trace_id=trace_id,
    )
    metrics = metrics or {}
    model = metrics.get("model") or ""
    cost = estimate_cost_usd(model, metrics.get("prompt_tokens"), metrics.get("completion_tokens"))
    append_message(
        db,
        conv,
        content=output,
        message_type="agent",
        role="assistant",
        created_by=user_id,
        agent_ref=agent_id,
        model=model,
        provider=metrics.get("provider_type") or "",
        prompt_tokens=metrics.get("prompt_tokens"),
        completion_tokens=metrics.get("completion_tokens"),
        latency_ms=int(metrics.get("latency_ms") or 0) or None,
        cost_usd=cost,
        trace_id=trace_id,
        tool_calls=tool_results or [],
        knowledge_refs=[{"knowledge_id": knowledge_id}] if knowledge_id else [],
        meta={
            "selected_tools": selected_tools or [],
            "metrics": metrics,
            "knowledge_id": knowledge_id,
        },
    )
    return {"conversation_id": conv.id}


def load_history_for_runtime(
    db: Session,
    conversation_id: str,
    *,
    workspace_id: int,
    limit: int = 12,
) -> list[dict[str, str]]:
    msgs = get_messages(db, conversation_id, workspace_id=workspace_id, limit=limit)
    return messages_as_history(msgs)
