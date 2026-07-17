import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import Assistant, SessionLocal, User, Workflow
from app.deps import effective_role
from app.services.tenancy import ensure_personal_workspace, get_membership
from app.services.knowledge import rag_context_for_assistant, rag_hits_for_assistant
from app.services.llm import stream_chat
from app.services.receipt import build_chat_receipt
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
):
    from app.services.ab_routing import pick_ab_model
    from app.services.workspace_settings import get_chat_config

    ab_meta = None
    model_name = ""
    if workspace_id:
        cfg = get_chat_config(db)
        model_name = cfg.get("model") or ""
        ab_meta = pick_ab_model(db, workspace_id, model_name)

    await websocket.send_json({"type": "start"})
    buffer = ""
    usage_out: dict = {}
    stopped = False
    async for token in stream_chat(
        system,
        user_msg,
        db=db,
        workspace_id=workspace_id,
        cancel_event=cancel_event,
        usage_out=usage_out,
        history=history,
    ):
        if cancel_event is not None and cancel_event.is_set():
            stopped = True
            break
        buffer += token
        await websocket.send_json(
            {"type": "stream", "message": {"content": token, "reasoning_content": ""}}
        )
        await asyncio.sleep(0)
    if cancel_event is not None and cancel_event.is_set():
        stopped = True
    receipt = build_chat_receipt(
        model=ab_meta.get("model") if ab_meta else model_name,
        rag_hits=(receipt_extra or {}).get("rag_hits"),
        ab_meta=ab_meta,
        chars=len(buffer),
        event_type=event_type,
        usage=usage_out,
        stopped=stopped,
    )
    await websocket.send_json({"type": "end", "message": {"content": buffer}, "receipt": receipt})
    await websocket.send_json({"type": "close"})
    meta = {"chars": len(buffer), "stopped": stopped}
    if usage_out.get("total_tokens") is not None:
        meta["total_tokens"] = usage_out.get("total_tokens")
        meta["prompt_tokens"] = usage_out.get("prompt_tokens")
        meta["completion_tokens"] = usage_out.get("completion_tokens")
    if ab_meta:
        meta["ab_variant"] = ab_meta.get("variant")
        meta["ab_model"] = ab_meta.get("model")
        meta["ab_route_id"] = ab_meta.get("route_id")
    log_usage(db, user_id, event_type, resource_id, meta, workspace_id)


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
        wid, _role = ws_ctx

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
            # Prefer last user turn for retrieval; fall back to full query
            rag_query = query
            if history:
                # Light rewrite: include previous user question for follow-ups
                prev_users = [h["content"] for h in history if h["role"] == "user"][-2:]
                if prev_users and len(query.split()) <= 8:
                    rag_query = f"{' '.join(prev_users[-1:])} {query}".strip()
            rag_hits = rag_hits_for_assistant(db, assistant_id, rag_query)
            rag = rag_context_for_assistant(db, assistant_id, rag_query)
            system_prompt = assistant.prompt
            if rag:
                system_prompt = (
                    f"{assistant.prompt}\n\n"
                    "Use the retrieved context when it is relevant. Prefer: direct answer first, "
                    "then short supporting bullets. Cite sources as [n] when you rely on a passage. "
                    "If context is empty or does not help, say what is missing and answer cautiously.\n\n"
                    f"--- Retrieved context ---\n{rag}\n--- End context ---"
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
                    assistant_id,
                    "chat",
                    system_prompt,
                    query,
                    wid,
                    receipt_extra={"rag_hits": rag_hits},
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
