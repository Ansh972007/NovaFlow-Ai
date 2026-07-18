"""Memory integration — conversation summaries and runtime memory."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.conversation.service import get_messages, messages_as_history
from app.database import Conversation
from app.runtime.context import RuntimeContext
from app.runtime.memory import MemoryRequest, resolve_memory, store_memory


def load_conversation_memory(
    ctx: RuntimeContext,
    conversation: Conversation,
    *,
    limit: int = 12,
) -> str:
    msgs = get_messages(ctx.db, conversation.id, workspace_id=conversation.workspace_id, limit=limit)
    history = messages_as_history(msgs)
    bundle = resolve_memory(
        ctx,
        MemoryRequest(
            history=history,
            assistant_id=conversation.resource_id if conversation.conversation_type == "assistant" else "",
            session_id=conversation.id,
        ),
    )
    if conversation.summary:
        return f"{conversation.summary}\n\n{bundle.combined()}".strip()
    return bundle.combined()


async def summarize_conversation(ctx: RuntimeContext, conversation: Conversation) -> str:
    from app.runtime.execution import execute_chat_sync

    msgs = get_messages(ctx.db, conversation.id, workspace_id=conversation.workspace_id, limit=40)
    if not msgs:
        return ""
    lines = []
    for m in msgs[-20:]:
        lines.append(f"{m.role}: {(m.content or '')[:400]}")
    blob = "\n".join(lines)
    summary = await execute_chat_sync(
        ctx,
        "Summarize this conversation in 3–5 sentences. Include key decisions and open items.",
        blob[:8000],
    )
    conversation.summary = (summary or "")[:4000]
    ctx.db.commit()
    store_memory(
        ctx.db,
        workspace_id=conversation.workspace_id,
        scope="conversation",
        content=summary or "",
        scope_ref=conversation.id,
        user_id=ctx.user_id,
    )
    return summary or ""
