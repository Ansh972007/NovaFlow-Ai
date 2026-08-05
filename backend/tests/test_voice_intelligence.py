"""Voice Intelligence automated test suite."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path

# Isolate tests from the developer's local SQLite so we never mutate production-ish data.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-voice-test-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-test-secret"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
from tests.conftest import TEST_ADMIN_PASSWORD
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.voice.base import BaseSTTProvider, BaseTTSProvider
from app.voice.service import VoiceService
from app.voice.stt import GoogleSTTProvider, MockSTTProvider, STTFailoverManager, WhisperSTTProvider
from app.voice.tts import ElevenLabsTTSProvider, MockTTSProvider, OpenAITTSProvider, TTSFailoverManager
from tests.test_smoke import _auth_headers


class FailingSTTProvider(BaseSTTProvider):
    @property
    def provider_name(self) -> str:
        return "failing_stt"

    async def transcribe_stream(self, audio_generator, language_code="en"):
        yield ""

    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        raise RuntimeError("API limit exceeded")


class FailingTTSProvider(BaseTTSProvider):
    @property
    def provider_name(self) -> str:
        return "failing_tts"

    async def synthesize_stream(self, text_generator):
        yield b""

    async def synthesize_text(self, text: str) -> bytes:
        raise RuntimeError("API limit exceeded")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_stt_failover():
    primary = FailingSTTProvider()
    backup = MockSTTProvider()
    manager = STTFailoverManager(primary, backup)

    res = asyncio.run(manager.transcribe_file(b"test audio data"))
    assert res == "mock file transcription completed successfully"
    assert not manager.primary_healthy


def test_tts_failover():
    primary = FailingTTSProvider()
    backup = MockTTSProvider()
    manager = TTSFailoverManager(primary, backup)

    res = asyncio.run(manager.synthesize_text("test synthesis text"))
    assert len(res) > 0
    assert not manager.primary_healthy


def test_intent_classification():
    service = VoiceService()

    # Navigation intents
    nav = service.classify_intent("navigate to workspace settings")
    assert nav.action == "navigate"
    assert nav.target == "workspace_settings"

    nav2 = service.classify_intent("go to dashboard")
    assert nav2.action == "navigate"
    assert nav2.target == "dashboard"

    # Workflow controls
    wf = service.classify_intent("run workflow daily_compliance")
    assert wf.action == "workflow.run"
    assert wf.target == "daily_compliance"

    wf2 = service.classify_intent("pause workflow 12")
    assert wf2.action == "workflow.pause"
    assert wf2.target == "12"

    # Chat fallback
    chat = service.classify_intent("What is the temperature of the server room?")
    assert chat.action == "chat"
    assert chat.params["query"] == "What is the temperature of the server room?"


def test_voice_websocket_lifecycle(client):
    headers = _auth_headers(client)
    token = headers["Authorization"].split(" ")[1]

    with client.websocket_connect(f"/api/v1/voice/stream?token={token}") as ws:
        # Step 1: Handshake and Session readiness check
        ready_msg = ws.receive_json()
        assert ready_msg["type"] == "session_ready"
        assert ready_msg["workspace_id"] is not None

        # Step 2: Upload audio bytes and receive transcription and base64 audio response
        ws.send_bytes(b"\x00\xff" * 50)
        
        transcript_msg = ws.receive_json()
        assert transcript_msg["type"] == "transcript"
        assert transcript_msg["text"]

        intent_msg = ws.receive_json()
        assert intent_msg["type"] == "intent"
        assert intent_msg["action"] in (
            "chat",
            "suggest",
            "workflow.run",
            "workflow.pause",
            "workflow.stop",
            "workflow.resume",
            "workflow.approve",
            "navigate",
        )

        # Receive streaming audio synthesis or confirmation logs
        if intent_msg["action"] == "chat":
            audio_msg = ws.receive_json()
            assert audio_msg["type"] == "audio"
            assert audio_msg["data"]
            # Validate Base64 encoding
            decoded = base64.b64decode(audio_msg["data"])
            assert len(decoded) > 0

        # Step 3: Send interruption signal
        ws.send_json({"action": "stop"})
        interrupted_msg = ws.receive_json()
        assert interrupted_msg["type"] == "interrupted"


# Helper for running async method inside sync pytest execution context
import asyncio
