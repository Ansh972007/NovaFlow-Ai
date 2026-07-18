"""AI conversation features — titles, tags, categorization."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.conversation.memory import summarize_conversation
from app.conversation.service import get_messages
from app.database import Conversation
from app.runtime.context import RuntimeContext


async def generate_title(ctx: RuntimeContext, conversation: Conversation) -> str:
    from app.runtime.execution import execute_chat_sync

    msgs = get_messages(ctx.db, conversation.id, workspace_id=conversation.workspace_id, limit=6)
    if not msgs:
        return conversation.title or "New conversation"
    first_user = next((m.content for m in msgs if m.role == "user"), "")
    title = await execute_chat_sync(
        ctx,
        "Generate a short conversation title (max 8 words). Output the title only.",
        (first_user or "")[:1000],
    )
    title = (title or "").strip().strip('"')[:200]
    if title:
        conversation.title = title
        ctx.db.commit()
    return title or conversation.title


async def suggest_tags(ctx: RuntimeContext, conversation: Conversation) -> list[str]:
    import json
    import re

    from app.runtime.execution import execute_chat_sync

    msgs = get_messages(ctx.db, conversation.id, workspace_id=conversation.workspace_id, limit=10)
    blob = "\n".join((m.content or "")[:200] for m in msgs[-6:])
    raw = await execute_chat_sync(
        ctx,
        'Suggest 3–5 tags as a JSON array of strings. Output JSON only.',
        blob[:3000],
    )
    match = re.search(r"\[[\s\S]*\]", raw or "")
    tags = []
    if match:
        try:
            tags = json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    if tags:
        conversation.tags_json = json.dumps(tags[:8])
        ctx.db.commit()
    return tags if isinstance(tags, list) else []
