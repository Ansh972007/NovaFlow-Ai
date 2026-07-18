"""Export engine — Markdown, JSON, HTML."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.conversation.service import conversation_dict, get_conversation, get_messages, message_dict


def export_conversation(
    db: Session,
    conversation_id: str,
    *,
    workspace_id: int,
    fmt: str = "markdown",
) -> dict[str, Any]:
    c = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not c:
        return {"error": "Conversation not found"}
    msgs = get_messages(db, conversation_id, workspace_id=workspace_id, limit=500)
    if fmt == "json":
        return {
            "format": "json",
            "content": json.dumps(
                {"conversation": conversation_dict(c), "messages": [message_dict(m) for m in msgs]},
                ensure_ascii=False,
                indent=2,
            ),
        }
    if fmt == "html":
        parts = [f"<h1>{c.title or 'Conversation'}</h1>"]
        for m in msgs:
            parts.append(f"<div class='msg {m.role}'><strong>{m.role}</strong><p>{m.content or ''}</p></div>")
        return {"format": "html", "content": "\n".join(parts)}

    lines = [f"# {c.title or 'Conversation'}", ""]
    if c.summary:
        lines.extend([f"> {c.summary}", ""])
    for m in msgs:
        label = m.role.title()
        lines.append(f"## {label}")
        lines.append(m.content or "")
        lines.append("")
    return {"format": "markdown", "content": "\n".join(lines)}
