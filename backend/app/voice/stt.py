"""Speech-to-Text (STT) providers and failover implementation."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from app.voice.base import BaseSTTProvider

logger = logging.getLogger(__name__)


class WhisperSTTProvider(BaseSTTProvider):
    """OpenAI Whisper Speech-to-Text provider."""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self._is_healthy = True

    @property
    def provider_name(self) -> str:
        return "whisper"

    async def transcribe_stream(
        self,
        audio_generator: AsyncIterator[bytes],
        language_code: str = "en",
    ) -> AsyncIterator[str]:
        """Simulated streaming transcription for Whisper (chunked audio)."""
        buffer = b""
        async for chunk in audio_generator:
            buffer += chunk
            if len(buffer) >= 16000:  # Emit a simulated word block
                yield "voice "
                buffer = b""
        yield "command detected"

    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        """Mock file transcription for Whisper."""
        if not audio_bytes:
            return ""
        return "simulate workflow execution"


class GoogleSTTProvider(BaseSTTProvider):
    """Google Cloud Speech-to-Text provider."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._is_healthy = True

    @property
    def provider_name(self) -> str:
        return "google_speech"

    async def transcribe_stream(
        self,
        audio_generator: AsyncIterator[bytes],
        language_code: str = "en",
    ) -> AsyncIterator[str]:
        async for _ in audio_generator:
            yield "google speech "
        yield "transcript finished"

    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        return "google standard voice prompt"


class MockSTTProvider(BaseSTTProvider):
    """Mock STT provider for local testing and failover safety."""

    @property
    def provider_name(self) -> str:
        return "mock_stt"

    async def transcribe_stream(
        self,
        audio_generator: AsyncIterator[bytes],
        language_code: str = "en",
    ) -> AsyncIterator[str]:
        # Consume stream
        async for _ in audio_generator:
            pass
        yield "mock transcript results"

    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        return "mock file transcription completed successfully"


class STTFailoverManager:
    """Manages active STT providers and implements automatic failover."""

    def __init__(self, primary: BaseSTTProvider, backup: BaseSTTProvider):
        self.primary = primary
        self.backup = backup
        self.primary_healthy = True

    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        if self.primary_healthy:
            try:
                return await self.primary.transcribe_file(audio_bytes, language_code)
            except Exception as exc:
                logger.error(f"Primary STT ({self.primary.provider_name}) failed: {exc}. Failing over.")
                self.primary_healthy = False
        
        logger.info(f"Using backup STT provider: {self.backup.provider_name}")
        return await self.backup.transcribe_file(audio_bytes, language_code)
