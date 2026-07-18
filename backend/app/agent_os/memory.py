"""AgentOS memory integration."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import AIMemoryEntry


def load_agent_memory(db: Session, *, workspace_id: int, agent_id: str, limit: int = 8) -> list[dict]:
    rows = (
        db.query(AIMemoryEntry)
        .filter(
            AIMemoryEntry.workspace_id == workspace_id,
            AIMemoryEntry.scope == "agent",
            AIMemoryEntry.scope_ref == agent_id,
            AIMemoryEntry.deleted_at.is_(None),
        )
        .order_by(AIMemoryEntry.update_time.desc())
        .limit(limit)
        .all()
    )
    return [{"id": r.id, "content": r.content, "pinned": bool(r.pinned)} for r in rows]


def save_execution_memory(
    db: Session,
    *,
    workspace_id: int,
    agent_id: str,
    content: str,
    user_id: int | None = None,
    meta: dict | None = None,
) -> AIMemoryEntry:
    entry = AIMemoryEntry(
        workspace_id=workspace_id,
        scope="agent",
        scope_ref=agent_id,
        user_id=user_id,
        content=(content or "")[:4000],
        meta_json=json.dumps(meta or {}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def load_conversation_history(
    db: Session,
    *,
    conversation_id: str | None,
    workspace_id: int,
    limit: int = 12,
) -> list[dict[str, str]]:
    if not conversation_id:
        return []
    from app.conversation.integration import load_history_for_runtime

    return load_history_for_runtime(db, conversation_id, workspace_id=workspace_id, limit=limit)


def memory_context(memories: list[dict], history: list[dict]) -> str:
    parts = []
    if memories:
        parts.append("## Agent memory\n" + "\n".join(f"- {m['content'][:300]}" for m in memories[:5]))
    if history:
        parts.append("## Recent conversation\n" + "\n".join(f"{h['role']}: {h['content'][:200]}" for h in history[-6:]))
    return "\n\n".join(parts)
