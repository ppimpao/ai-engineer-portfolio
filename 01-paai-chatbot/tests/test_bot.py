"""
Tests for the Telegram voice handler — no Telegram, no API server.
The Telegram message and the HTTP call to the API are replaced with fakes.
"""

import base64
import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")

import bot
from core.config import settings


def make_update(chat_type="private", duration=5):
    """A fake Telegram update carrying a voice note."""
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"OggS-note"))

    message = MagicMock()
    message.chat.id = 42
    message.chat.type = chat_type
    message.voice.duration = duration
    message.voice.mime_type = "audio/ogg"
    message.voice.get_file = AsyncMock(return_value=tg_file)
    message.reply_text = AsyncMock()
    message.reply_voice = AsyncMock()

    update = MagicMock()
    update.message = message
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    return update, context


def api_reply(**overrides):
    reply = {
        "transcript": "What is Saturn?",
        "response": "A gas giant with rings.",
        "audio_b64": base64.b64encode(b"OggS-reply").decode(),
        "fallback_reason": None,
        "reply_chars": 23,
        "spoken_chars": 23,
        "spoken_by": "direct",
        "send_text": False,
    }
    reply.update(overrides)
    return reply


@pytest.fixture
def fake_api(monkeypatch):
    """Replace call_api; records calls and returns whatever the test sets."""
    calls = []
    state = {"reply": api_reply(), "error": None}

    def _call_api(endpoint, method="POST", **kwargs):
        calls.append((endpoint, kwargs))
        if state["error"]:
            raise RuntimeError(state["error"])
        return state["reply"]

    monkeypatch.setattr(bot, "call_api", _call_api)
    return calls, state


@pytest.mark.asyncio
async def test_voice_note_gets_voice_reply_with_transcript_caption(fake_api):
    calls, _ = fake_api
    update, context = make_update()
    await bot.handle_voice(update, context)

    assert calls[0][0] == "/voice/chat"
    sent = update.message.reply_voice.call_args.kwargs
    assert sent["voice"] == b"OggS-reply"
    assert "What is Saturn?" in sent["caption"]
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_summarised_reply_also_sends_full_text(fake_api):
    _, state = fake_api
    state["reply"] = api_reply(reply_chars=900, spoken_chars=200, spoken_by="summary", send_text=True)
    update, context = make_update()
    await bot.handle_voice(update, context)

    update.message.reply_voice.assert_called_once()
    update.message.reply_text.assert_called_once_with("A gas giant with rings.")


@pytest.mark.asyncio
async def test_api_fallback_is_answered_with_text(fake_api):
    _, state = fake_api
    state["reply"] = api_reply(audio_b64=None, fallback_reason="tts_failed")
    update, context = make_update()
    await bot.handle_voice(update, context)

    update.message.reply_voice.assert_not_called()
    update.message.reply_text.assert_called_once_with("A gas giant with rings.")


@pytest.mark.asyncio
@pytest.mark.parametrize("duration", [600, timedelta(minutes=10)])
async def test_long_note_rejected_before_download(fake_api, duration):
    calls, _ = fake_api
    update, context = make_update(duration=duration)
    await bot.handle_voice(update, context)

    update.message.voice.get_file.assert_not_called()  # no download, no credits spent
    assert calls == []
    assert str(settings.max_voice_seconds) in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_type", ["group", "supergroup"])
async def test_voice_in_groups_is_ignored(fake_api, chat_type):
    calls, _ = fake_api
    update, context = make_update(chat_type=chat_type)
    await bot.handle_voice(update, context)

    assert calls == []
    update.message.reply_text.assert_not_called()
    update.message.reply_voice.assert_not_called()


@pytest.mark.asyncio
async def test_api_down_gets_apology_not_crash(fake_api):
    _, state = fake_api
    state["error"] = "Cannot reach the API server. Is it running?"
    update, context = make_update()
    await bot.handle_voice(update, context)

    assert "couldn't process your voice note" in update.message.reply_text.call_args.args[0]
