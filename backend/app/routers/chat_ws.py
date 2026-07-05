import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import Assistant, SessionLocal, User, Workflow
from app.deps import effective_role
from app.services.tenancy import ensure_personal_workspace, get_membership
from app.services.knowledge import rag_context_for_assistant
from app.services.llm import stream_chat
from app.services.workflow import log_usage, resolve_workflow_llm_messages, run_workflow_with_progress

router = APIRouter(tags=["Chat"])


def get_user_id_from_ws(websocket: WebSocket) -> int | None:
    token = websocket.query_params.get("t") or websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return int(payload["sub"])


def get_ws_workspace(db: Session, websocket: WebSocket, user_id: int) -> tuple[int, str] | None:
    raw = websocket.query_params.get("workspace_id")
    if raw:
        try:
            wid = int(raw)
        except ValueError:
            return None
        membership = get_membership(db, user_id, wid)
        if not membership:
            return None
        return wid, membership.role or "editor"

    user = db.get(User, user_id)
    if not user:
        return None
    ws = ensure_personal_workspace(db, user)
    membership = get_membership(db, user_id, ws.id)
    return ws.id, (membership.role if membership else "editor")


def _parse_user_message(payload: dict) -> str:
    return (
        payload.get("inputs", {}).get("input")
        or payload.get("data", {}).get("dialog_input", {}).get("message")
        or payload.get("data", {}).get("dialog_input", {}).get("data", {}).get("user_input")
        or ""
    )


async def _stream_reply(
    websocket: WebSocket,
    db: Session,
    user_id: int,
    resource_id: str,
    event_type: str,
    system: str,
    user_msg: str,
    workspace_id: int | None = None,
):
    await websocket.send_json({"type": "start"})
    buffer = ""
    async for token in stream_chat(system, user_msg):
        buffer += token
        await websocket.send_json(
            {"type": "stream", "message": {"content": token, "reasoning_content": ""}}
        )
        await asyncio.sleep(0)
    await websocket.send_json({"type": "end", "message": {"content": buffer}})
    await websocket.send_json({"type": "close"})
    log_usage(db, user_id, event_type, resource_id, {"chars": len(buffer)}, workspace_id)


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

            rag = rag_context_for_assistant(db, assistant_id, str(user_msg).strip())
            system_prompt = assistant.prompt
            if rag:
                system_prompt = (
                    f"{assistant.prompt}\n\n"
                    "Use the following retrieved context when relevant. "
                    "If context does not help, answer from general knowledge.\n\n"
                    f"--- Context ---\n{rag}\n--- End context ---"
                )
            await _stream_reply(
                websocket,
                db,
                user_id,
                assistant_id,
                "chat",
                system_prompt,
                str(user_msg).strip(),
                wid,
            )
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

            system, llm_user = await resolve_workflow_llm_messages(
                db, workflow, user_id, str(user_msg).strip()
            )
            await _stream_reply(
                websocket,
                db,
                user_id,
                workflow.id,
                "workflow_chat",
                system,
                llm_user,
                wid,
            )
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
        if ws_role == "viewer" or effective_role(user) == "viewer":
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
