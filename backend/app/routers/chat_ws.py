import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.crypto import decode_token
from app.database import Assistant, ConversationAttachment, SessionLocal, User, Workflow
from app.deps import effective_role
from app.services.tenancy import ensure_personal_workspace, get_membership
from app.services.knowledge import rag_hits_for_assistant
from app.services.workflow import log_usage, resolve_workflow_llm_messages, run_workflow_with_progress

router = APIRouter(tags=["Chat"])


def get_user_id_from_ws(websocket: WebSocket) -> int | None:
    from app.security.rate_limit import rate_limiter
    from app.security.config import RATE_LIMIT_WS_PER_MINUTE
    from app.security.tokens import session_is_active

    # Prefer Authorization header; fall back to query token for browser WS clients.
    token = None
    auth = websocket.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = websocket.query_params.get("t") or websocket.query_params.get("token")
    if not token:
        return None
    client = websocket.client.host if websocket.client else "ws"
    if not rate_limiter.allow("ws", client, limit=RATE_LIMIT_WS_PER_MINUTE, window_seconds=60):
        return None
    payload = decode_token(token)
    if not payload:
        return None
    sid = payload.get("sid")
    if sid:
        db = SessionLocal()
        try:
            if not session_is_active(db, sid):
                return None
        finally:
            db.close()
    return int(payload["sub"])


def get_ws_workspace(db: Session, websocket: WebSocket, user_id: int) -> tuple[int, str] | None:
    """Resolve tenant for WebSocket — same kernel as HTTP (emergency + soft-delete)."""
    from app.platform.context import resolve_tenant
    from app.platform.emergency import expire_stale_grants
    from app.platform.permissions import workspace_has_permission
    from app.security.rbac import Permission

    user = db.get(User, user_id)
    if not user or user.delete:
        return None

    raw = websocket.query_params.get("workspace_id")
    wid = None
    if raw:
        try:
            wid = int(raw)
        except ValueError:
            return None

    expire_stale_grants(db)
    try:
        tenant = resolve_tenant(db, user, workspace_id=wid, request=None)
    except Exception:
        return None

    # Subscriptions require at least read permission on assistants/workflows
    if not workspace_has_permission(
        tenant.role,
        Permission.ASSISTANT_READ,
        via_emergency_access=tenant.via_emergency_access,
    ):
        return None

    return tenant.workspace_id, tenant.role

def _parse_user_message(payload: dict) -> str:
    from app.security.ai_guard import sanitize_user_prompt

    raw = (
        payload.get("inputs", {}).get("input")
        or payload.get("data", {}).get("dialog_input", {}).get("message")
        or payload.get("data", {}).get("dialog_input", {}).get("data", {}).get("user_input")
        or ""
    )
    return sanitize_user_prompt(str(raw))


def _parse_chat_history(payload: dict) -> list[dict]:
    """Accept prior turns from the client (role + content)."""
    raw = payload.get("chatHistory") or payload.get("history") or []
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        role = (row.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (row.get("content") or row.get("message") or "").strip()
        if content:
            out.append({"role": role, "content": content})
    return out


def _parse_attachment_ids(payload: dict) -> list[str]:
    raw = payload.get("attachment_ids") or payload.get("attachmentIds") or []
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x or "").strip()][:20]


def _attachment_texts(db: Session, *, workspace_id: int, attachment_ids: list[str]) -> list[str]:
    if not attachment_ids:
        return []
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.id.in_(attachment_ids),
            ConversationAttachment.deleted_at.is_(None),
        )
        .all()
    )
    texts: list[str] = []
    for row in rows:
        if not row.storage_key:
            continue
        p = UPLOAD_DIR / Path(row.storage_key)
        sidecar = p.with_suffix(p.suffix + ".txt")
        if sidecar.exists():
            try:
                txt = sidecar.read_text(encoding="utf-8", errors="ignore").strip()
                if txt:
                    texts.append(f"[Attachment: {row.file_name}]\n{txt[:8000]}")
            except Exception:
                pass
    return texts[:6]


async def _stream_reply(
    websocket: WebSocket,
    db: Session,
    user_id: int,
    resource_id: str,
    event_type: str,
    system: str,
    user_msg: str,
    workspace_id: int | None = None,
    receipt_extra: dict | None = None,
    cancel_event: asyncio.Event | None = None,
    history: list[dict] | None = None,
    *,
    assistant_id: str = "",
    rag_query: str | None = None,
    attachment_ids: list[str] | None = None,
):
    from app.runtime.context import RuntimeContext
    from app.runtime.pipeline import AIRuntime, ChatRequest
    from app.runtime.providers import resolve_provider
    from app.runtime.router import route_model
    from app.services.receipt import build_chat_receipt

    role = (receipt_extra or {}).get("role") or "editor"
    ctx = RuntimeContext.from_ws(
        db,
        user_id=user_id,
        workspace_id=workspace_id or 0,
        role=role,
        cancel_event=cancel_event,
    )
    runtime = AIRuntime(ctx)

    provider = resolve_provider(db)
    route = route_model(db, workspace_id, provider)
    ab_meta = None
    if route.route_id:
        ab_meta = {"model": route.model, "variant": route.variant, "route_id": route.route_id}
    elif route.model:
        ab_meta = {"model": route.model, "variant": route.variant, "route_id": route.route_id}

    await websocket.send_json({"type": "start"})
    buffer = ""
    usage_out: dict = {}
    stopped = False
    rag_hits = (receipt_extra or {}).get("rag_hits")

    req = ChatRequest(
        user_message=user_msg,
        system_prompt=system,
        assistant_id=assistant_id,
        history=history,
        rag_query=rag_query or user_msg,
    )
    try:
        async for token in runtime.chat_stream(req, usage_out=usage_out):
            if cancel_event is not None and cancel_event.is_set():
                stopped = True
                break
            buffer += token
            await websocket.send_json(
                {"type": "stream", "message": {"content": token, "reasoning_content": ""}}
            )
            await asyncio.sleep(0)
    except Exception as exc:
        await websocket.send_json({"type": "error", "category": "error", "message": str(exc)})
        await websocket.send_json({"type": "close"})
        return

    if cancel_event is not None and cancel_event.is_set():
        stopped = True
    if not rag_hits and assistant_id:
        from app.runtime.knowledge import resolve_assistant_knowledge

        kb = resolve_assistant_knowledge(ctx, assistant_id, rag_query or user_msg)
        rag_hits = [h.to_dict() for h in kb.hits]

    receipt = build_chat_receipt(
        model=ab_meta.get("model") if ab_meta else (usage_out.get("model") or ""),
        rag_hits=rag_hits,
        ab_meta=ab_meta,
        chars=len(buffer),
        event_type=event_type,
        usage=usage_out,
        stopped=stopped,
    )
    try:
        from app.composer.chat_powerhouse import accumulate_receipt

        accumulate_receipt(
            db,
            conversation_id=(receipt_extra or {}).get("conversation_id"),
            usage=usage_out,
            model=str(receipt.get("model") or ""),
        )
    except Exception:
        pass
    await websocket.send_json({"type": "end", "message": {"content": buffer}, "receipt": receipt})
    await websocket.send_json({"type": "close"})
    meta = {"chars": len(buffer), "stopped": stopped, "trace_id": ctx.trace_id}
    if usage_out.get("total_tokens") is not None:
        meta["total_tokens"] = usage_out.get("total_tokens")
        meta["prompt_tokens"] = usage_out.get("prompt_tokens")
        meta["completion_tokens"] = usage_out.get("completion_tokens")
    if ab_meta:
        meta["ab_variant"] = ab_meta.get("variant")
        meta["ab_model"] = ab_meta.get("model")
        meta["ab_route_id"] = ab_meta.get("route_id")
    log_usage(db, user_id, event_type, resource_id, meta, workspace_id)

    try:
        from app.conversation.integration import persist_chat_turn

        conv_meta = persist_chat_turn(
            db,
            workspace_id=workspace_id or 0,
            user_id=user_id,
            organization_id=None,
            assistant_id=assistant_id or resource_id,
            user_message=user_msg,
            assistant_message=buffer,
            conversation_id=(receipt_extra or {}).get("conversation_id"),
            usage=usage_out,
            rag_hits=rag_hits,
            trace_id=ctx.trace_id,
            event_type=event_type,
            attachment_ids=attachment_ids or [],
        )
        await websocket.send_json({"type": "conversation", "conversation_id": conv_meta.get("conversation_id")})
    except Exception:
        pass


@router.websocket("/assistant/chat/{assistant_id}")
async def assistant_chat_ws(websocket: WebSocket, assistant_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "category": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "category": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, role = ws_ctx

        assistant = db.get(Assistant, assistant_id)
        if not assistant or assistant.workspace_id != wid:
            await websocket.send_json({"type": "error", "category": "error", "message": "Assistant not found"})
            await websocket.close()
            return

        init_raw = await websocket.receive_text()
        try:
            json.loads(init_raw)
        except json.JSONDecodeError:
            pass

        if assistant.desc:
            await websocket.send_json(
                {
                    "category": "guide_word",
                    "message": {"guide_word": assistant.desc, "msg": assistant.desc},
                }
            )

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("action") == "stop":
                continue

            user_msg = _parse_user_message(payload)
            if not str(user_msg).strip():
                continue

            query = str(user_msg).strip()
            history = _parse_chat_history(payload)
            attachment_ids = _parse_attachment_ids(payload)
            conversation_id = payload.get("conversation_id") or websocket.query_params.get("conversation_id")
            if conversation_id and not history:
                try:
                    from app.conversation.integration import load_history_for_runtime

                    history = load_history_for_runtime(db, conversation_id, workspace_id=wid)
                except Exception:
                    pass
            # Prefer last user turn for retrieval; fall back to full query
            rag_query = query
            if history:
                # Light rewrite: include previous user question for follow-ups
                prev_users = [h["content"] for h in history if h["role"] == "user"][-2:]
                if prev_users and len(query.split()) <= 8:
                    rag_query = f"{' '.join(prev_users[-1:])} {query}".strip()
            rag_hits = rag_hits_for_assistant(db, assistant_id, rag_query)
            system_prompt = assistant.prompt
            attachment_context = _attachment_texts(db, workspace_id=wid, attachment_ids=attachment_ids)
            if attachment_context:
                query = query + "\n\nAttached context:\n" + "\n\n".join(attachment_context)

            try:
                from app.composer.chat_bridge import process_chat_turn

                bridge = await process_chat_turn(
                    db,
                    workspace_id=wid,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_message=str(user_msg).strip(),
                    workspace_role=role,
                )
            except Exception:
                bridge = {"events": [], "blocked_normal_reply": False}

            for ev in (bridge.get("ui_events") or bridge.get("events") or []):
                # Send only UI card(s) — typically one primary event
                await websocket.send_json(ev)
                # Stop after first card for blocked AIOS (one reply unit)
                if bridge.get("blocked_normal_reply"):
                    break
            if bridge.get("blocked_normal_reply"):
                summary = (bridge.get("summary") or "").strip()
                if not summary:
                    summary = "Done — use the buttons on the card."
                await websocket.send_json(
                    {"type": "end", "message": {"content": summary}, "receipt": {"event_type": "aios"}}
                )
                try:
                    from app.conversation.integration import persist_chat_turn

                    conv_meta = persist_chat_turn(
                        db,
                        workspace_id=wid,
                        user_id=user_id,
                        organization_id=None,
                        assistant_id=assistant_id,
                        user_message=(bridge.get("redacted_message") or str(user_msg)).strip(),
                        assistant_message=summary,
                        conversation_id=conversation_id,
                        attachment_ids=attachment_ids,
                        event_type="chat",
                    )
                    await websocket.send_json(
                        {"type": "conversation", "conversation_id": conv_meta.get("conversation_id")}
                    )
                except Exception:
                    pass
                await websocket.send_json({"type": "close"})
                continue

            cancel_event = asyncio.Event()

            async def _watch_stop(evt: asyncio.Event):
                while not evt.is_set():
                    try:
                        raw_stop = await websocket.receive_text()
                    except Exception:
                        evt.set()
                        return
                    try:
                        stop_payload = json.loads(raw_stop)
                    except json.JSONDecodeError:
                        continue
                    if stop_payload.get("action") == "stop":
                        evt.set()
                        return

            watcher = asyncio.create_task(_watch_stop(cancel_event))
            try:
                await _stream_reply(
                    websocket,
                    db,
                    user_id,
                    assistant_id,
                    "chat",
                    system_prompt,
                    query,
                    wid,
                    receipt_extra={"rag_hits": rag_hits, "role": role, "conversation_id": conversation_id},
                    cancel_event=cancel_event,
                    history=history,
                    assistant_id=assistant_id,
                    rag_query=rag_query,
                    attachment_ids=attachment_ids,
                )
            finally:
                cancel_event.set()
                watcher.cancel()
                try:
                    await watcher
                except asyncio.CancelledError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


@router.websocket("/workflow/chat/{workflow_id}")
async def workflow_chat_ws(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "category": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "category": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, _role = ws_ctx

        workflow = db.get(Workflow, workflow_id)
        if not workflow or workflow.workspace_id != wid:
            await websocket.send_json({"type": "error", "category": "error", "message": "Workflow not found"})
            await websocket.close()
            return
        if workflow.status != 1:
            await websocket.send_json({"type": "error", "category": "error", "message": "Workflow is not published"})
            await websocket.close()
            return

        init_raw = await websocket.receive_text()
        try:
            json.loads(init_raw)
        except json.JSONDecodeError:
            pass

        if workflow.desc:
            await websocket.send_json(
                {
                    "category": "guide_word",
                    "message": {"guide_word": workflow.desc, "msg": workflow.desc},
                }
            )

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("action") == "stop":
                continue

            user_msg = _parse_user_message(payload)
            if not str(user_msg).strip():
                continue

            history = _parse_chat_history(payload)
            system, llm_user = await resolve_workflow_llm_messages(
                db, workflow, user_id, str(user_msg).strip()
            )
            cancel_event = asyncio.Event()

            async def _watch_stop(evt: asyncio.Event):
                while not evt.is_set():
                    try:
                        raw_stop = await websocket.receive_text()
                    except Exception:
                        evt.set()
                        return
                    try:
                        stop_payload = json.loads(raw_stop)
                    except json.JSONDecodeError:
                        continue
                    if stop_payload.get("action") == "stop":
                        evt.set()
                        return

            watcher = asyncio.create_task(_watch_stop(cancel_event))
            try:
                await _stream_reply(
                    websocket,
                    db,
                    user_id,
                    workflow.id,
                    "workflow_chat",
                    system,
                    llm_user,
                    wid,
                    cancel_event=cancel_event,
                    history=history,
                )
            finally:
                cancel_event.set()
                watcher.cancel()
                try:
                    await watcher
                except asyncio.CancelledError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


@router.websocket("/workflow/run/ws/{workflow_id}")
async def workflow_run_ws(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, ws_role = ws_ctx

        user = db.get(User, user_id)
        if not user or user.delete:
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
            await websocket.close()
            return
        from app.platform.roles import has_workspace_min_role

        if not has_workspace_min_role(ws_role, "editor"):
            await websocket.send_json({"type": "error", "message": "Viewer access is read-only"})
            await websocket.close()
            return

        workflow = db.get(Workflow, workflow_id)
        if not workflow or workflow.workspace_id != wid:
            await websocket.send_json({"type": "error", "message": "Workflow not found"})
            await websocket.close()
            return

        raw = await websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid payload"})
            await websocket.close()
            return

        user_input = (payload.get("input") or "").strip()
        if not user_input:
            await websocket.send_json({"type": "error", "message": "Input required"})
            await websocket.close()
            return

        async def emit(event: dict):
            await websocket.send_json(event)

        await run_workflow_with_progress(db, workflow, user_id, user_input, emit, workspace_id=wid)
        await websocket.send_json({"type": "close"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
