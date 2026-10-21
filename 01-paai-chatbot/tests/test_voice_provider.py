"""
Unit tests for the voice provider layer — no network, no API key.
"""

import asyncio
import os

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")

from elevenlabs.core.api_error import ApiError

from core.config import settings
from core.voice.base import VoiceError
from core.voice.elevenlabs import ElevenLabsVoiceProvider
from core.voice.factory import get_voice_provider
from core.voice.null import NullVoiceProvider


@pytest.fixture
def voice_settings():
    """Restore voice settings after each test that changes them."""
    saved = (settings.voice_provider, settings.elevenlabs_api_key, settings.elevenlabs_voice_id)
    yield settings
    settings.voice_provider, settings.elevenlabs_api_key, settings.elevenlabs_voice_id = saved


# ── Factory ────────────────────────────────────────────────────────────────────

def test_factory_none_disables_voice(voice_settings):
    voice_settings.voice_provider = "none"
    assert isinstance(get_voice_provider(), NullVoiceProvider)


def test_factory_missing_key_disables_voice(voice_settings):
    voice_settings.voice_provider = "elevenlabs"
    voice_settings.elevenlabs_api_key = ""
    voice_settings.elevenlabs_voice_id = "some-voice"
    assert isinstance(get_voice_provider(), NullVoiceProvider)


def test_factory_configured_returns_elevenlabs(voice_settings):
    voice_settings.voice_provider = "elevenlabs"
    voice_settings.elevenlabs_api_key = "fake-key"
    voice_settings.elevenlabs_voice_id = "some-voice"
    assert isinstance(get_voice_provider(), ElevenLabsVoiceProvider)


def test_factory_unknown_provider_raises(voice_settings):
    voice_settings.voice_provider = "whisper"
    with pytest.raises(ValueError):
        get_voice_provider()


# ── Null provider ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_null_provider_fails_cleanly():
    provider = NullVoiceProvider()
    with pytest.raises(VoiceError) as exc:
        await provider.transcribe(b"audio", "note.ogg")
    assert exc.value.reason == "disabled"


# ── Error translation ──────────────────────────────────────────────────────────

def make_provider(timeout: float = 30.0) -> ElevenLabsVoiceProvider:
    return ElevenLabsVoiceProvider(api_key="fake-key", voice_id="v", timeout=timeout)


@pytest.mark.asyncio
@pytest.mark.parametrize("status, reason", [
    (401, "auth"),          # the real "key missing speech_to_text permission" case
    (402, "plan_limit"),    # the real "free users cannot use library voices" case
    (429, "rate_limited"),
    (422, "bad_audio"),
    (500, "unavailable"),
])
async def test_api_errors_become_voice_errors(status, reason):
    async def failing_call():
        raise ApiError(status_code=status, body={"detail": "boom"})

    with pytest.raises(VoiceError) as exc:
        await make_provider()._guarded(failing_call())
    assert exc.value.reason == reason


@pytest.mark.asyncio
async def test_slow_call_becomes_timeout():
    async def slow_call():
        await asyncio.sleep(1)

    with pytest.raises(VoiceError) as exc:
        await make_provider(timeout=0.01)._guarded(slow_call())
    assert exc.value.reason == "timeout"
