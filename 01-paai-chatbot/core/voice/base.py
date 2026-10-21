from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Transcript:
    text: str
    language: str | None = None


class VoiceError(Exception):
    """A voice call failed. `reason` is a short, loggable category, not a message for the user."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason  # "disabled" | "auth" | "plan_limit" | "rate_limited" | "bad_audio" | "timeout" | "unavailable"
        self.detail = detail


class VoiceProvider(ABC):
    """Common interface for speech-to-text and text-to-speech backends."""

    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str) -> Transcript:
        """Turn recorded audio into text."""
        ...

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Turn text into encoded audio (format set by configuration)."""
        ...
