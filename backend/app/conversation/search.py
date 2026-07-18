"""Enterprise conversation search — full-text + filters."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.conversation.service import conversation_dict, message_dict
from app.database import Conversation, ConversationMessage


def search_conversations(
    db: Session,
    *,
    workspace_id: int,
    query: str = "",
    conversation_type: str | None = None,
    assistant_id: str | None = None,
    model: str | None = None,
    message_type: str | None = None,
    pinned_only: bool = False,
    starred_only: bool = False,
    since: datetime | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    cq = db.query(Conversation).filter(
        Conversation.workspace_id == workspace_id,
        Conversation.deleted_at.is_(None),
        Conversation.status == "active",
    )
    if conversation_type:
        cq = cq.filter(Conversation.conversation_type == conversation_type)
    if pinned_only:
        cq = cq.filter(Conversation.pinned == 1)
    if starred_only:
        cq = cq.filter(Conversation.starred == 1)
    if since:
        cq = cq.filter(Conversation.update_time >= since)
    if assistant_id:
        cq = cq.filter(Conversation.resource_id == assistant_id)

    conversations = cq.order_by(Conversation.update_time.desc()).limit(limit * 2).all()
    conv_hits = []
    msg_hits = []

    q = (query or "").strip()
    if q:
        tokens = [t for t in re.findall(r"\w+", q.lower()) if len(t) > 1]
        for c in conversations:
            title = (c.title or "").lower()
            summary = (c.summary or "").lower()
            if any(t in title or t in summary for t in tokens):
                conv_hits.append(conversation_dict(c))

        mq = db.query(ConversationMessage).filter(
            ConversationMessage.workspace_id == workspace_id,
            ConversationMessage.deleted_at.is_(None),
        )
        if message_type:
            mq = mq.filter(ConversationMessage.message_type == message_type)
        if model:
            mq = mq.filter(ConversationMessage.model.contains(model))
        if assistant_id:
            mq = mq.filter(ConversationMessage.assistant_id == assistant_id)
        if since:
            mq = mq.filter(ConversationMessage.create_time >= since)

        for m in mq.order_by(ConversationMessage.create_time.desc()).limit(200):
            text = (m.content or "").lower()
            if tokens and not any(t in text for t in tokens):
                continue
            if q.lower() in text or not tokens:
                msg_hits.append(message_dict(m))
            if len(msg_hits) >= limit:
                break
    else:
        conv_hits = [conversation_dict(c) for c in conversations[:limit]]

    return {
        "query": q,
        "conversations": conv_hits[:limit],
        "messages": msg_hits[:limit],
        "total_conversations": len(conv_hits),
        "total_messages": len(msg_hits),
    }
