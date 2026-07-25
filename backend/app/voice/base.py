"""Base interfaces and configuration schemas for Voice Intelligence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class VoiceResult:
    """Standardized result envelope for voice operations."""
    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }


class BaseSTTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the STT provider (e.g., 'whisper', 'azure_speech')."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_generator: AsyncIterator[bytes],
        language_code: str = "en",
    ) -> AsyncIterator[str]:
        """Stream raw audio chunks and yield transcribed text fragments."""
        yield ""

    @abstractmethod
    async def transcribe_file(self, audio_bytes: bytes, language_code: str = "en") -> str:
        """Transcribe a full static audio file and return the complete text."""
        pass


class BaseTTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the TTS provider (e.g., 'openai_tts', 'elevenlabs')."""
        pass

    @abstractmethod
    async def synthesize_stream(self, text_generator: AsyncIterator[str]) -> AsyncIterator[bytes]:
        """Stream text tokens and yield synthesized raw MP3/PCM audio chunks."""
        yield b""

    @abstractmethod
    async def synthesize_text(self, text: str) -> bytes:
        """Synthesize static text input and return complete audio bytes."""
        pass
