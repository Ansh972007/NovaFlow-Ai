"""Retention — soft delete, legal hold, cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import Conversation, ConversationMessage


def soft_delete_conversation(db: Session, conversation: Conversation) -> None:
    if conversation.legal_hold:
        raise ValueError("Conversation under legal hold")
    conversation.deleted_at = datetime.utcnow()
    conversation.status = "deleted"
    db.commit()


def set_legal_hold(db: Session, conversation: Conversation, hold: bool = True) -> None:
    conversation.legal_hold = 1 if hold else 0
    db.commit()


def cleanup_deleted(db: Session, *, days: int = 30) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(Conversation)
        .filter(
            Conversation.deleted_at.isnot(None),
            Conversation.deleted_at < cutoff,
            Conversation.legal_hold == 0,
        )
        .all()
    )
    count = 0
    for c in rows:
        db.query(ConversationMessage).filter(ConversationMessage.conversation_id == c.id).delete()
        db.delete(c)
        count += 1
    if count:
        db.commit()
    return count
