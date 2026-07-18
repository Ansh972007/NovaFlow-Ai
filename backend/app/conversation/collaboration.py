"""Collaboration — sharing, permissions."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database import Conversation, ConversationShare


def create_share_link(
    db: Session,
    conversation: Conversation,
    *,
    created_by: int,
    permission: str = "read",
    expires_hours: int = 72,
) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    row = ConversationShare(
        id=secrets.token_hex(16),
        conversation_id=conversation.id,
        workspace_id=conversation.workspace_id,
        created_by=created_by,
        share_token=token,
        permission=permission,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    db.add(row)
    conversation.visibility = "shared"
    db.commit()
    return {"share_token": token, "permission": permission, "expires_at": row.expires_at.isoformat()}


def resolve_share(db: Session, token: str) -> Conversation | None:
    row = db.query(ConversationShare).filter(ConversationShare.share_token == token).first()
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.utcnow():
        return None
    return db.get(Conversation, row.conversation_id)
