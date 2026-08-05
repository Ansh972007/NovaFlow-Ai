"""Conversation service — CRUD with tenant isolation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import Conversation, ConversationMessage, ConversationThread

MESSAGE_TYPES = frozenset(
    {"user", "assistant", "system", "tool", "workflow", "knowledge", "agent", "notification", "approval", "comment"}
)
CONVERSATION_TYPES = frozenset(
    {"assistant", "knowledge", "workflow", "agent", "evaluation", "marketplace", "api", "voice", "desktop", "browser", "mobile"}
)


def _json_loads(raw: str, default=None):
    try:
        return json.loads(raw or "")
    except json.JSONDecodeError:
        return default if default is not None else {}


def conversation_dict(c: Conversation, *, message_count: int = 0) -> dict[str, Any]:
    return {
        "id": c.id,
        "workspace_id": c.workspace_id,
        "organization_id": c.organization_id,
        "user_id": c.user_id,
        "title": c.title or "",
        "summary": c.summary or "",
        "tags": _json_loads(c.tags_json, []),
        "conversation_type": c.conversation_type,
        "resource_id": c.resource_id or "",
        "visibility": c.visibility,
        "status": c.status,
        "pinned": bool(c.pinned),
        "starred": bool(c.starred),
        "message_count": message_count,
        "create_time": c.create_time.isoformat() if c.create_time else None,
        "update_time": c.update_time.isoformat() if c.update_time else None,
    }


def message_dict(m: ConversationMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "thread_id": m.thread_id,
        "parent_message_id": m.parent_message_id,
        "message_type": m.message_type,
        "role": m.role,
        "content": m.content or "",
        "created_by": m.created_by,
        "assistant_id": m.assistant_id or "",
        "model": m.model or "",
        "provider": m.provider or "",
        "prompt_tokens": m.prompt_tokens,
        "completion_tokens": m.completion_tokens,
        "latency_ms": m.latency_ms,
        "cost_usd": m.cost_usd,
        "trace_id": m.trace_id or "",
        "knowledge_refs": _json_loads(m.knowledge_refs_json, []),
        "tool_calls": _json_loads(m.tool_calls_json, []),
        "citations": _json_loads(m.citations_json, []),
        "workflow_ref": m.workflow_ref or "",
        "agent_ref": m.agent_ref or "",
        "attachment_ids": _json_loads(m.attachment_ids_json, []),
        "meta": _json_loads(m.meta_json, {}),
        "version": m.version,
        "create_time": m.create_time.isoformat() if m.create_time else None,
    }


def create_conversation(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    organization_id: int | None = None,
    title: str = "New conversation",
    conversation_type: str = "assistant",
    resource_id: str = "",
    visibility: str = "private",
    meta: dict | None = None,
) -> Conversation:
    c = Conversation(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title=(title or "New conversation")[:200],
        conversation_type=conversation_type if conversation_type in CONVERSATION_TYPES else "assistant",
        resource_id=resource_id or "",
        visibility=visibility,
        meta_json=json.dumps(meta or {}),
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(c)
    thread = ConversationThread(id=uuid.uuid4().hex, conversation_id=c.id, title="Main")
    db.add(thread)
    db.commit()
    db.refresh(c)
    return c


def get_conversation(db: Session, conversation_id: str, *, workspace_id: int) -> Conversation | None:
    c = db.get(Conversation, conversation_id)
    if not c or c.workspace_id != workspace_id or c.deleted_at is not None:
        return None
    return c


def list_conversations(
    db: Session,
    *,
    workspace_id: int,
    user_id: int | None = None,
    conversation_type: str | None = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> list[Conversation]:
    q = db.query(Conversation).filter(
        Conversation.workspace_id == workspace_id,
        Conversation.deleted_at.is_(None),
    )
    if status:
        q = q.filter(Conversation.status == status)
    if user_id:
        q = q.filter(Conversation.user_id == user_id)
    if conversation_type:
        q = q.filter(Conversation.conversation_type == conversation_type)
    return q.order_by(Conversation.update_time.desc()).offset(offset).limit(limit).all()


def append_message(
    db: Session,
    conversation: Conversation,
    *,
    content: str,
    message_type: str = "user",
    role: str = "user",
    created_by: int | None = None,
    thread_id: str | None = None,
    parent_message_id: str | None = None,
    assistant_id: str = "",
    model: str = "",
    provider: str = "",
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    trace_id: str = "",
    knowledge_refs: list | None = None,
    tool_calls: list | None = None,
    citations: list | None = None,
    workflow_ref: str = "",
    agent_ref: str = "",
    attachment_ids: list[str] | None = None,
    meta: dict | None = None,
) -> ConversationMessage:
    if not thread_id:
        thread = (
            db.query(ConversationThread)
            .filter(ConversationThread.conversation_id == conversation.id)
            .order_by(ConversationThread.create_time.asc())
            .first()
        )
        thread_id = thread.id if thread else None

    msg = ConversationMessage(
        id=uuid.uuid4().hex,
        conversation_id=conversation.id,
        thread_id=thread_id,
        parent_message_id=parent_message_id,
        workspace_id=conversation.workspace_id,
        organization_id=conversation.organization_id,
        message_type=message_type if message_type in MESSAGE_TYPES else "user",
        role=role,
        content=(content or "")[:32000],
        created_by=created_by or conversation.user_id,
        assistant_id=assistant_id,
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        trace_id=trace_id,
        knowledge_refs_json=json.dumps(knowledge_refs or []),
        tool_calls_json=json.dumps(tool_calls or []),
        citations_json=json.dumps(citations or []),
        workflow_ref=workflow_ref,
        agent_ref=agent_ref,
        attachment_ids_json=json.dumps(attachment_ids or []),
        meta_json=json.dumps(meta or {}),
    )
    db.add(msg)
    conversation.update_time = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(
    db: Session,
    conversation_id: str,
    *,
    workspace_id: int,
    thread_id: str | None = None,
    limit: int = 100,
    before_id: str | None = None,
) -> list[ConversationMessage]:
    c = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not c:
        return []
    q = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id,
        ConversationMessage.deleted_at.is_(None),
    )
    if thread_id:
        q = q.filter(ConversationMessage.thread_id == thread_id)
    if before_id:
        ref = db.get(ConversationMessage, before_id)
        if ref and ref.create_time:
            q = q.filter(ConversationMessage.create_time < ref.create_time)
    return q.order_by(ConversationMessage.create_time.asc()).limit(limit).all()


def get_or_create_for_resource(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    organization_id: int | None,
    conversation_type: str,
    resource_id: str,
    conversation_id: str | None = None,
) -> Conversation:
    if conversation_id:
        c = get_conversation(db, conversation_id, workspace_id=workspace_id)
        if c:
            return c
    rows = (
        db.query(Conversation)
        .filter(
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
            Conversation.conversation_type == conversation_type,
            Conversation.resource_id == resource_id,
            Conversation.status == "active",
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.update_time.desc())
        .limit(1)
        .all()
    )
    if rows:
        return rows[0]
    return create_conversation(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        organization_id=organization_id,
        conversation_type=conversation_type,
        resource_id=resource_id,
    )


def messages_as_history(messages: list[ConversationMessage]) -> list[dict[str, str]]:
    out = []
    for m in messages:
        if m.message_type in ("user", "assistant") and m.role in ("user", "assistant"):
            out.append({"role": m.role, "content": m.content or ""})
    return out
