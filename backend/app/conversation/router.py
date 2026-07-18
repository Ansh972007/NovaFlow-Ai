"""Enterprise Conversation API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.conversation.ai_features import generate_title, suggest_tags
from app.conversation.collaboration import create_share_link, resolve_share
from app.conversation.export import export_conversation
from app.conversation.integration import load_history_for_runtime
from app.conversation.memory import summarize_conversation
from app.conversation.retention import set_legal_hold, soft_delete_conversation
from app.conversation.search import search_conversations
from app.conversation.service import (
    append_message,
    conversation_dict,
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations,
    message_dict,
)
from app.conversation.threading import (
    archive_conversation,
    create_snapshot,
    fork_conversation,
    merge_branch,
    pin_conversation,
    restore_conversation as restore_thread,
)
from app.database import Conversation, get_db
from app.deps import get_workspace_ctx, require_permission, require_workspace_editor
from app.runtime.context import runtime_from_platform
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["Conversations"])


@router.post("/conversations")
def api_create_conversation(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = create_conversation(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        organization_id=ctx.organization_id,
        title=(body.get("title") or "New conversation").strip(),
        conversation_type=body.get("conversation_type") or body.get("type") or "assistant",
        resource_id=(body.get("resource_id") or body.get("assistant_id") or "").strip(),
        visibility=body.get("visibility") or "private",
        meta=body.get("meta"),
    )
    ctx.audit("conversation.create", resource_type="conversation", resource_id=c.id)
    return ok(conversation_dict(c))


@router.get("/conversations")
def api_list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conversation_type: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    rows = list_conversations(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        conversation_type=conversation_type,
        limit=limit,
        offset=offset,
    )
    return ok([conversation_dict(r) for r in rows])


@router.get("/conversations/{conversation_id}")
def api_get_conversation(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    msgs = get_messages(db, conversation_id, workspace_id=ctx.workspace_id, limit=500)
    return ok({**conversation_dict(c, message_count=len(msgs)), "messages": [message_dict(m) for m in msgs]})


@router.post("/conversations/{conversation_id}/messages")
def api_create_message(conversation_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    msg = append_message(
        db,
        c,
        content=(body.get("content") or body.get("message") or "").strip(),
        message_type=body.get("message_type") or body.get("role") or "user",
        role=body.get("role") or "user",
        created_by=ctx.user.user_id,
        thread_id=body.get("thread_id"),
        parent_message_id=body.get("parent_message_id"),
        assistant_id=body.get("assistant_id") or c.resource_id,
        meta=body.get("meta"),
    )
    ctx.audit("conversation.message.create", resource_type="conversation", resource_id=conversation_id)
    return ok(message_dict(msg))


@router.get("/conversations/{conversation_id}/messages")
def api_list_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    thread_id: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    msgs = get_messages(db, conversation_id, workspace_id=ctx.workspace_id, thread_id=thread_id, limit=limit)
    if not msgs and not get_conversation(db, conversation_id, workspace_id=ctx.workspace_id):
        return fail(404, "Conversation not found")
    return ok([message_dict(m) for m in msgs])


@router.post("/conversations/search")
def api_search(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(
        search_conversations(
            db,
            workspace_id=ctx.workspace_id,
            query=body.get("q") or body.get("query") or "",
            conversation_type=body.get("conversation_type"),
            assistant_id=body.get("assistant_id"),
            model=body.get("model"),
            message_type=body.get("message_type"),
            pinned_only=bool(body.get("pinned")),
            starred_only=bool(body.get("starred")),
            limit=min(int(body.get("limit") or 30), 100),
        )
    )


@router.post("/conversations/{conversation_id}/archive")
def api_archive(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    archive_conversation(db, c)
    return ok({"archived": conversation_id})


@router.post("/conversations/{conversation_id}/restore")
def api_restore(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = db.get(Conversation, conversation_id)
    if not c or c.workspace_id != ctx.workspace_id:
        return fail(404, "Conversation not found")
    restore_thread(db, c)
    return ok({"restored": conversation_id})


@router.post("/conversations/{conversation_id}/delete")
def api_delete(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    try:
        soft_delete_conversation(db, c)
    except ValueError as exc:
        return fail(400, str(exc))
    return ok({"deleted": conversation_id})


@router.post("/conversations/{conversation_id}/fork")
def api_fork(conversation_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    result = fork_conversation(db, c, parent_message_id=body.get("parent_message_id"), user_id=ctx.user.user_id)
    return ok(result)


@router.post("/conversations/branches/{branch_id}/merge")
def api_merge_branch(branch_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    return ok(merge_branch(db, branch_id, workspace_id=ctx.workspace_id))


@router.post("/conversations/{conversation_id}/snapshot")
def api_snapshot(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    version = create_snapshot(db, c, user_id=ctx.user.user_id)
    return ok({"version": version})


@router.get("/conversations/{conversation_id}/export")
def api_export(
    conversation_id: str,
    fmt: str = Query("markdown"),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    result = export_conversation(db, conversation_id, workspace_id=ctx.workspace_id, fmt=fmt)
    if result.get("error"):
        return fail(404, result["error"])
    return ok(result)


@router.post("/conversations/{conversation_id}/summarize")
async def api_summarize(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    summary = await summarize_conversation(runtime_from_platform(ctx), c)
    return ok({"summary": summary})


@router.post("/conversations/{conversation_id}/title")
async def api_title(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    title = await generate_title(runtime_from_platform(ctx), c)
    return ok({"title": title})


@router.post("/conversations/{conversation_id}/tags")
async def api_tags(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    tags = await suggest_tags(runtime_from_platform(ctx), c)
    return ok({"tags": tags})


@router.post("/conversations/{conversation_id}/share")
def api_share(conversation_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    c = get_conversation(db, conversation_id, workspace_id=ctx.workspace_id)
    if not c:
        return fail(404, "Conversation not found")
    link = create_share_link(
        db,
        c,
        created_by=ctx.user.user_id,
        permission=body.get("permission") or "read",
        expires_hours=int(body.get("expires_hours") or 72),
    )
    ctx.audit("conversation.share", resource_type="conversation", resource_id=conversation_id)
    return ok(link)


@router.get("/conversations/shared/{token}")
def api_shared(token: str, db: Session = Depends(get_db)):
    c = resolve_share(db, token)
    if not c:
        return fail(404, "Share link invalid or expired")
    msgs = get_messages(db, c.id, workspace_id=c.workspace_id, limit=200)
    return ok({**conversation_dict(c, message_count=len(msgs)), "messages": [message_dict(m) for m in msgs]})


@router.get("/conversations/{conversation_id}/history")
def api_history(conversation_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    history = load_history_for_runtime(db, conversation_id, workspace_id=ctx.workspace_id)
    return ok({"history": history})
