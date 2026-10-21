from .base import VoiceProvider, Transcript, VoiceError


class NullVoiceProvider(VoiceProvider):
    """Used when voice is turned off or not configured. Every call fails cleanly."""

    async def transcribe(self, audio: bytes, filename: str) -> Transcript:
        raise VoiceError("disabled", "voice provider is not configured")

    async def synthesize(self, text: str) -> bytes:
        raise VoiceError("disabled", "voice provider is not configured")
