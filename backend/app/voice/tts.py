"""Text-to-Speech (TTS) providers and failover implementation."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from app.voice.base import BaseTTSProvider

logger = logging.getLogger(__name__)


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI Audio Speech synthesis provider."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._is_healthy = True

    @property
    def provider_name(self) -> str:
        return "openai_tts"

    async def synthesize_stream(self, text_generator: AsyncIterator[str]) -> AsyncIterator[bytes]:
        """Simulate streaming synthesis by generating small PCM voice-like packets."""
        async for token in text_generator:
            if token.strip():
                # Emit mock binary audio bytes matching the token block length
                yield b"\x00\xff" * len(token)

    async def synthesize_text(self, text: str) -> bytes:
        """Return static mock audio bytes."""
        if not text:
            return b""
        return b"\x00\xff" * len(text)


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs voice synthesis provider."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._is_healthy = True

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize_stream(self, text_generator: AsyncIterator[str]) -> AsyncIterator[bytes]:
        async for token in text_generator:
            if token.strip():
                yield b"\xff\x00" * len(token)

    async def synthesize_text(self, text: str) -> bytes:
        if not text:
            return b""
        return b"\xff\x00" * len(text)


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS provider for local offline execution."""

    @property
    def provider_name(self) -> str:
        return "mock_tts"

    async def synthesize_stream(self, text_generator: AsyncIterator[str]) -> AsyncIterator[bytes]:
        async for token in text_generator:
            yield b"\xaa\x55" * len(token)

    async def synthesize_text(self, text: str) -> bytes:
        return b"\xaa\x55" * len(text)


class TTSFailoverManager:
    """Manages active TTS providers and handles automatic failover routing."""

    def __init__(self, primary: BaseTTSProvider, backup: BaseTTSProvider):
        self.primary = primary
        self.backup = backup
        self.primary_healthy = True

    async def synthesize_text(self, text: str) -> bytes:
        if self.primary_healthy:
            try:
                return await self.primary.synthesize_text(text)
            except Exception as exc:
                logger.error(f"Primary TTS ({self.primary.provider_name}) failed: {exc}. Failing over.")
                self.primary_healthy = False

        logger.info(f"Using backup TTS provider: {self.backup.provider_name}")
        return await self.backup.synthesize_text(text)
