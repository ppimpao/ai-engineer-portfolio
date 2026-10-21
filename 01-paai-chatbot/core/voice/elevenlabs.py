import asyncio

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core.api_error import ApiError

from .base import VoiceProvider, Transcript, VoiceError


def _reason_for_status(status: int | None) -> str:
    if status in (401, 403):
        return "auth"          # bad key, or key missing a permission
    if status == 402:
        return "plan_limit"    # feature not in the current plan (e.g. library voices on free tier)
    if status == 429:
        return "rate_limited"  # includes running out of credits
    if status in (400, 413, 415, 422):
        return "bad_audio"
    return "unavailable"


class ElevenLabsVoiceProvider(VoiceProvider):
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        stt_model: str = "scribe_v2",
        tts_model: str = "eleven_flash_v2_5",
        output_format: str = "opus_48000_64",
        timeout: float = 30.0,
    ):
        self.client = AsyncElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.output_format = output_format
        self.timeout = timeout

    async def transcribe(self, audio: bytes, filename: str) -> Transcript:
        async def call():
            # tag_audio_events=False: silence must come back empty, not as "(silence)"
            return await self.client.speech_to_text.convert(
                file=(filename, audio),
                model_id=self.stt_model,
                tag_audio_events=False,
            )

        result = await self._guarded(call())
        return Transcript(text=(result.text or "").strip(), language=result.language_code)

    async def synthesize(self, text: str) -> bytes:
        async def call():
            stream = self.client.text_to_speech.convert(
                self.voice_id,
                text=text,
                model_id=self.tts_model,
                output_format=self.output_format,
            )
            return b"".join([chunk async for chunk in stream])

        return await self._guarded(call())

    async def _guarded(self, coro):
        """Run an SDK call with a timeout and translate failures into VoiceError."""
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout)
        except asyncio.TimeoutError:
            raise VoiceError("timeout", f"no response within {self.timeout:.0f}s")
        except ApiError as e:
            raise VoiceError(_reason_for_status(e.status_code), str(e.body)[:200])
        except Exception as e:  # network errors, unexpected SDK errors
            raise VoiceError("unavailable", f"{type(e).__name__}: {e}"[:200])
