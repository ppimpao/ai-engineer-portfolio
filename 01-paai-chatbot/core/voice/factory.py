import logging

from .base import VoiceProvider
from .null import NullVoiceProvider
from core.config import settings

logger = logging.getLogger(__name__)


def get_voice_provider() -> VoiceProvider:
    if settings.voice_provider == "none":
        return NullVoiceProvider()
    elif settings.voice_provider == "elevenlabs":
        # Voice is optional: missing config disables it instead of stopping the app.
        if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
            logger.warning("ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID not set — voice disabled.")
            return NullVoiceProvider()
        from .elevenlabs import ElevenLabsVoiceProvider
        return ElevenLabsVoiceProvider(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            stt_model=settings.elevenlabs_stt_model,
            tts_model=settings.elevenlabs_tts_model,
            output_format=settings.voice_output_format,
        )
    else:
        raise ValueError(f"Unknown VOICE_PROVIDER: '{settings.voice_provider}'. Use 'elevenlabs' or 'none'.")
