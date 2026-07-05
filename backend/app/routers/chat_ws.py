import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.crypto import decode_token
from app.database import Assistant, SessionLocal
from app.services.knowledge import rag_context_for_assistant
from app.services.llm import stream_chat
from app.services.workflow import log_usage

router = APIRouter(tags=["Chat"])


def get_user_id_from_ws(websocket: WebSocket) -> int | None:
    token = websocket.query_params.get("t") or websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return int(payload["sub"])


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
        assistant = db.get(Assistant, assistant_id)
        if not assistant or assistant.user_id != user_id:
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

            user_msg = (
                payload.get("inputs", {}).get("input")
                or payload.get("data", {}).get("dialog_input", {}).get("message")
                or ""
            )
            if not str(user_msg).strip():
                continue

            await websocket.send_json({"type": "start"})
            buffer = ""
            rag = rag_context_for_assistant(db, assistant_id, str(user_msg).strip())
            system_prompt = assistant.prompt
            if rag:
                system_prompt = (
                    f"{assistant.prompt}\n\n"
                    "Use the following retrieved context when relevant. "
                    "If context does not help, answer from general knowledge.\n\n"
                    f"--- Context ---\n{rag}\n--- End context ---"
                )
            async for token in stream_chat(system_prompt, str(user_msg).strip()):
                buffer += token
                await websocket.send_json(
                    {"type": "stream", "message": {"content": token, "reasoning_content": ""}}
                )
                await asyncio.sleep(0)
            await websocket.send_json({"type": "end", "message": {"content": buffer}})
            await websocket.send_json({"type": "close"})
            log_usage(db, user_id, "chat", assistant_id, {"chars": len(buffer)})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
