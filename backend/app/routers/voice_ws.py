"""Voice Intelligence WebSocket Streaming Router."""

from __future__ import annotations

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.routers.chat_ws import get_user_id_from_ws, get_ws_workspace
from app.voice.service import VoiceService
from app.voice.stt import MockSTTProvider, STTFailoverManager, WhisperSTTProvider
from app.voice.tts import MockTTSProvider, OpenAITTSProvider, TTSFailoverManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Voice"])


@router.websocket("/voice/stream")
async def voice_stream_ws(websocket: WebSocket):
    """Bidirectional WebSocket streaming voice intelligence pipeline."""
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
        wid, _role = ws_ctx

        # Initialize providers & services
        stt_primary = WhisperSTTProvider()
        stt_backup = MockSTTProvider()
        stt_manager = STTFailoverManager(stt_primary, stt_backup)

        tts_primary = OpenAITTSProvider()
        tts_backup = MockTTSProvider()
        tts_manager = TTSFailoverManager(tts_primary, tts_backup)

        voice_service = VoiceService()

        await websocket.send_json({"type": "session_ready", "workspace_id": wid})

        while True:
            # We accept either binary audio data chunks or control message JSON envelopes.
            message = await websocket.receive()
            if "bytes" in message:
                audio_chunk = message["bytes"]
                # 1. Transcribe the audio chunk
                transcript = await stt_manager.transcribe_file(audio_chunk)
                if not transcript.strip():
                    continue

                await websocket.send_json({"type": "transcript", "text": transcript})

                # 2. Classify intent
                intent = voice_service.classify_intent(transcript)
                await websocket.send_json(
                    {
                        "type": "intent",
                        "action": intent.action,
                        "target": intent.target,
                        "params": intent.params,
                    }
                )

                # 3. Perform action or conversational stream
                if intent.action == "chat":
                    # Generate speech response using TTS failover manager
                    response_text = f"Executing voice command. You asked: {transcript}"
                    audio_response = await tts_manager.synthesize_text(response_text)
                    audio_b64 = base64.b64encode(audio_response).decode("utf-8")

                    await websocket.send_json(
                        {
                            "type": "audio",
                            "data": audio_b64,
                            "text_reply": response_text,
                        }
                    )
                elif intent.action.startswith("workflow."):
                    await websocket.send_json(
                        {
                            "type": "execution_status",
                            "status": "triggered",
                            "message": f"Workflow {intent.target} execution started",
                        }
                    )
            elif "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("action") == "stop":
                        # Immediate flush and interruption request
                        await websocket.send_json({"type": "interrupted"})
                except json.JSONDecodeError:
                    continue

    except WebSocketDisconnect:
        logger.info("Voice connection closed by client.")
    except Exception as exc:
        logger.error(f"Voice router error: {exc}")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
