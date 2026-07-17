"""Memory engine — tenant-scoped conversation, workspace, agent, and pinned memory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.runtime.context import RuntimeContext

MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 4000
MAX_MEMORY_SNIPPETS = 8


@dataclass
class MemoryBundle:
    conversation: str = ""
    workspace: str = ""
    project: str = ""
    agent: str = ""
    pinned: str = ""
    semantic: str = ""

    def combined(self) -> str:
        parts = [p for p in (self.pinned, self.workspace, self.project, self.agent, self.semantic, self.conversation) if p.strip()]
        return "\n\n".join(parts)


@dataclass
class MemoryRequest:
    history: list[dict] | None = None
    assistant_id: str = ""
    agent_id: str = ""
    project_id: str = ""
    session_id: str = ""
    query: str = ""


def _normalize_history(history: list[dict] | None) -> list[dict[str, str]]:
    if not history:
        return []
    cleaned: list[dict[str, str]] = []
    for row in history:
        role = (row.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (row.get("content") or row.get("message") or "").strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return cleaned[-MAX_HISTORY_MESSAGES:]


def _history_to_text(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for row in history:
        label = "User" if row["role"] == "user" else "Assistant"
        lines.append(f"{label}: {row['content']}")
    return "\n".join(lines)


def _load_pinned(db: Session, workspace_id: int, *, scope_ref: str = "") -> list[str]:
    from app.database import AIMemoryEntry

    q = (
        db.query(AIMemoryEntry)
        .filter(
            AIMemoryEntry.workspace_id == workspace_id,
            AIMemoryEntry.pinned == 1,
            AIMemoryEntry.deleted_at.is_(None),
        )
        .order_by(AIMemoryEntry.update_time.desc())
        .limit(MAX_MEMORY_SNIPPETS)
    )
    if scope_ref:
        q = q.filter(AIMemoryEntry.scope_ref == scope_ref)
    return [(r.content or "").strip() for r in q.all() if (r.content or "").strip()]


def _load_scope_memory(db: Session, workspace_id: int, scope: str, scope_ref: str = "") -> list[str]:
    from app.database import AIMemoryEntry

    q = (
        db.query(AIMemoryEntry)
        .filter(
            AIMemoryEntry.workspace_id == workspace_id,
            AIMemoryEntry.scope == scope,
            AIMemoryEntry.deleted_at.is_(None),
        )
        .order_by(AIMemoryEntry.update_time.desc())
        .limit(MAX_MEMORY_SNIPPETS)
    )
    if scope_ref:
        q = q.filter(AIMemoryEntry.scope_ref == scope_ref)
    return [(r.content or "").strip() for r in q.all() if (r.content or "").strip()]


def resolve_memory(ctx: RuntimeContext, req: MemoryRequest) -> MemoryBundle:
    """Resolve all memory scopes for the current tenant."""
    db = ctx.db
    wid = ctx.workspace_id
    history = _normalize_history(req.history)
    bundle = MemoryBundle(conversation=_history_to_text(history))

    try:
        pinned = _load_pinned(db, wid, scope_ref=req.assistant_id or req.agent_id)
        if pinned:
            bundle.pinned = "\n".join(f"- {p}" for p in pinned)
    except Exception:
        pass

    try:
        ws_mem = _load_scope_memory(db, wid, "workspace")
        if ws_mem:
            bundle.workspace = "\n".join(f"- {p}" for p in ws_mem)
    except Exception:
        pass

    if req.project_id:
        try:
            proj = _load_scope_memory(db, wid, "project", req.project_id)
            if proj:
                bundle.project = "\n".join(f"- {p}" for p in proj)
        except Exception:
            pass

    if req.agent_id:
        try:
            agent_mem = _load_scope_memory(db, wid, "agent", req.agent_id)
            if agent_mem:
                bundle.agent = "\n".join(f"- {p}" for p in agent_mem)
        except Exception:
            pass

    return bundle


def store_memory(
    db: Session,
    *,
    workspace_id: int,
    scope: str,
    content: str,
    scope_ref: str = "",
    user_id: int | None = None,
    pinned: bool = False,
    meta: dict | None = None,
) -> int:
    """Persist a memory entry (tenant-scoped)."""
    from app.database import AIMemoryEntry

    row = AIMemoryEntry(
        workspace_id=workspace_id,
        scope=scope,
        scope_ref=scope_ref or "",
        user_id=user_id,
        content=(content or "").strip()[:8000],
        meta_json=json.dumps(meta or {}),
        pinned=1 if pinned else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return int(row.id)
