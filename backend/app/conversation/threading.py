"""Threading engine — branches, fork, merge, pin, archive."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.conversation.service import create_conversation, get_conversation, get_messages, message_dict
from app.database import Conversation, ConversationBranch, ConversationSnapshot, ConversationThread


def fork_conversation(
    db: Session,
    conversation: Conversation,
    *,
    parent_message_id: str | None,
    user_id: int,
) -> dict[str, Any]:
    branch_conv = create_conversation(
        db,
        workspace_id=conversation.workspace_id,
        user_id=user_id,
        organization_id=conversation.organization_id,
        title=f"Branch of {conversation.title or conversation.id[:8]}",
        conversation_type=conversation.conversation_type,
        resource_id=conversation.resource_id,
        meta={"forked_from": conversation.id, "parent_message_id": parent_message_id},
    )
    branch_conv.parent_branch_id = conversation.id
    branch = ConversationBranch(
        id=uuid.uuid4().hex,
        conversation_id=conversation.id,
        parent_message_id=parent_message_id,
        branch_conversation_id=branch_conv.id,
    )
    db.add(branch)
    db.commit()
    return {"branch_id": branch.id, "conversation_id": branch_conv.id}


def merge_branch(db: Session, branch_id: str, *, workspace_id: int) -> dict[str, Any]:
    branch = db.get(ConversationBranch, branch_id)
    if not branch:
        return {"ok": False, "error": "Branch not found"}
    parent = get_conversation(db, branch.conversation_id, workspace_id=workspace_id)
    child = get_conversation(db, branch.branch_conversation_id, workspace_id=workspace_id)
    if not parent or not child:
        return {"ok": False, "error": "Conversation not found"}
    branch.status = "merged"
    branch.merged_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "parent_id": parent.id, "merged_id": child.id}


def create_snapshot(db: Session, conversation: Conversation, *, user_id: int) -> int:
    msgs = get_messages(db, conversation.id, workspace_id=conversation.workspace_id, limit=500)
    snap = {
        "conversation": {"id": conversation.id, "title": conversation.title, "summary": conversation.summary},
        "messages": [message_dict(m) for m in msgs],
    }
    last = (
        db.query(ConversationSnapshot)
        .filter(ConversationSnapshot.conversation_id == conversation.id)
        .order_by(ConversationSnapshot.version_no.desc())
        .first()
    )
    version_no = (last.version_no + 1) if last else 1
    row = ConversationSnapshot(
        conversation_id=conversation.id,
        version_no=version_no,
        snapshot_json=json.dumps(snap),
        created_by=user_id,
    )
    db.add(row)
    db.commit()
    return version_no


def pin_conversation(db: Session, conversation: Conversation, pinned: bool = True) -> None:
    conversation.pinned = 1 if pinned else 0
    conversation.update_time = datetime.utcnow()
    db.commit()


def archive_conversation(db: Session, conversation: Conversation) -> None:
    conversation.status = "archived"
    conversation.archived_at = datetime.utcnow()
    db.commit()


def restore_conversation(db: Session, conversation: Conversation) -> None:
    conversation.status = "active"
    conversation.archived_at = None
    conversation.deleted_at = None
    db.commit()
