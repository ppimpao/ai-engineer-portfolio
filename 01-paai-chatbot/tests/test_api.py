"""
API tests for /chat and /voice/chat — no network, no API keys, no credits.
The LLM and voice provider are replaced with fakes; the database is temporary.
"""

import base64
import json
import os

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")

from fastapi.testclient import TestClient

import api
from core.config import settings
from core.llm.base import OUTPUT_LIMIT_NOTICE
from core.memory.manager import MemoryManager
from core.voice.base import Transcript, VoiceError, VoiceProvider


class FakeLLM:
    def __init__(self, reply: str | None = None):
        self.calls = 0
        self.reply = reply          # fixed reply; None means echo the question
        self.last_messages = None

    def estimate_tokens(self, text: str) -> int:
        return len(text.split())

    async def chat(self, messages, system):
        self.calls += 1
        self.last_messages = messages
        return self.reply if self.reply is not None else f"reply to: {messages[-1]['content']}"


LONG_STRUCTURED_REPLY = """# How Rockets Work

## Newton's Third Law
Every action has an **equal and opposite** reaction.

- Fuel burns in the combustion chamber
- Hot gas exits through the nozzle
"""


class FakeVoice(VoiceProvider):
    def __init__(self, transcript="Hello there", stt_error=None, tts_error=None):
        self.transcript = transcript
        self.stt_error = stt_error
        self.tts_error = tts_error
        self.spoken: list[str] = []

    async def transcribe(self, audio, filename):
        if self.stt_error:
            raise VoiceError(self.stt_error, "fake failure")
        return Transcript(text=self.transcript, language="eng")

    async def synthesize(self, text):
        if self.tts_error:
            raise VoiceError(self.tts_error, "fake failure")
        self.spoken.append(text)
        return b"OggS-fake-audio"


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Build a TestClient with fakes; pass a FakeVoice to control the voice path."""
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "voice_metrics_path", str(tmp_path / "metrics.jsonl"))
    clients = []

    def _make(fake_voice: VoiceProvider | None = None, reply: str | None = None,
              speech_llm: FakeLLM | None = None):
        llm = FakeLLM(reply)
        monkeypatch.setattr(api, "provider", llm)
        monkeypatch.setattr(api, "memory", MemoryManager(llm))
        monkeypatch.setattr(api, "speech_llm", speech_llm or FakeLLM("A short spoken summary."))
        monkeypatch.setattr(api, "voice", fake_voice or FakeVoice())
        client = TestClient(api.app)
        client.__enter__()  # runs the lifespan → creates the temp database
        clients.append(client)
        return client, llm

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


def send_voice(client, chat_id=1):
    return client.post(
        "/voice/chat",
        data={"chat_id": str(chat_id)},
        files={"audio": ("note.ogg", b"OggS-fake-note", "audio/ogg")},
    )


# ── /chat (behaviour unchanged by the run_chat_turn refactor) ─────────────────

def test_chat_replies_and_stores_both_messages(make_client):
    client, llm = make_client()
    r = client.post("/chat", json={"chat_id": 1, "text": "Hi"})
    assert r.status_code == 200
    assert r.json()["response"] == "reply to: Hi"
    assert client.get("/memory/1").json()["total_messages"] == 2


def test_chat_empty_message_never_reaches_llm(make_client):
    client, llm = make_client()
    r = client.post("/chat", json={"chat_id": 1, "text": "   "})
    assert r.status_code == 200
    assert llm.calls == 0


# ── /voice/chat happy path ─────────────────────────────────────────────────────

def test_voice_turn_returns_transcript_reply_and_audio(make_client):
    fake = FakeVoice(transcript="What is Saturn?")
    client, llm = make_client(fake)
    body = send_voice(client).json()

    assert body["transcript"] == "What is Saturn?"
    assert body["response"] == "reply to: What is Saturn?"
    assert base64.b64decode(body["audio_b64"]) == b"OggS-fake-audio"
    assert body["fallback_reason"] is None
    assert set(body["timings_ms"]) == {"stt", "llm", "tts", "total"}
    assert body["spoken_chars"] == len(fake.spoken[0])


def test_voice_and_text_share_memory(make_client):
    client, llm = make_client(FakeVoice(transcript="My name is Pedro"))
    send_voice(client, chat_id=7)
    client.post("/chat", json={"chat_id": 7, "text": "What's my name?"})
    # voice user + reply, text user + reply — one conversation
    assert client.get("/memory/7").json()["total_messages"] == 4


def test_tts_text_is_capped(make_client, monkeypatch):
    monkeypatch.setattr(settings, "max_tts_chars", 20)
    fake = FakeVoice(transcript="tell me a long story " * 10)
    client, llm = make_client(fake)
    body = send_voice(client).json()
    assert len(fake.spoken[0]) <= 20
    assert body["reply_chars"] > body["spoken_chars"]
    assert body["send_text"] is True  # the voice note was cut, so the full text follows


# ── /voice/chat spoken version: direct vs summary ─────────────────────────────

def test_short_plain_reply_is_spoken_directly(make_client):
    speech_llm = FakeLLM("should not be used")
    fake = FakeVoice(transcript="Hi")
    client, llm = make_client(fake, reply="Hi **Pedro**! Nice to meet you.", speech_llm=speech_llm)
    body = send_voice(client).json()

    assert body["spoken_by"] == "direct"
    assert body["send_text"] is False
    assert speech_llm.calls == 0                     # no extra model call, no extra latency
    assert fake.spoken[0] == "Hi Pedro! Nice to meet you."   # Markdown never reaches TTS
    assert "summary" not in body["timings_ms"]


def test_structured_reply_is_summarised_for_voice(make_client):
    speech_llm = FakeLLM("Rockets push gas down so the gas pushes them up. Details are in the text below.")
    fake = FakeVoice(transcript="How do rockets work?")
    client, llm = make_client(fake, reply=LONG_STRUCTURED_REPLY, speech_llm=speech_llm)
    body = send_voice(client).json()

    assert body["spoken_by"] == "summary"
    assert body["send_text"] is True
    assert body["response"] == LONG_STRUCTURED_REPLY           # the text message is the full answer
    assert fake.spoken[0].startswith("Rockets push gas down")  # the voice note is the summary
    prompt = speech_llm.last_messages[0]["content"]
    assert "How do rockets work?" in prompt and "Newton's Third Law" in prompt
    assert "summary" in body["timings_ms"]


def test_memory_keeps_full_answer_not_summary(make_client):
    client, llm = make_client(FakeVoice(transcript="How do rockets work?"), reply=LONG_STRUCTURED_REPLY)
    send_voice(client, chat_id=5)
    # The next text turn sends history to the main model: it must contain the full answer
    client.post("/chat", json={"chat_id": 5, "text": "And the nozzle?"})
    assert any(m["content"] == LONG_STRUCTURED_REPLY for m in llm.last_messages)


@pytest.mark.parametrize("speech_reply", [None, "   "])
def test_summary_failure_falls_back_to_cut_reply(make_client, speech_reply, monkeypatch):
    monkeypatch.setattr(settings, "max_tts_chars", 60)
    speech_llm = FakeLLM(speech_reply)
    if speech_reply is None:
        async def broken(messages, system):
            raise RuntimeError("Haiku down")
        speech_llm.chat = broken
    fake = FakeVoice(transcript="How do rockets work?")
    client, llm = make_client(fake, reply=LONG_STRUCTURED_REPLY, speech_llm=speech_llm)
    body = send_voice(client).json()

    assert body["spoken_by"] == "truncated"
    assert body["audio_b64"] is not None        # still a voice reply
    assert body["send_text"] is True
    assert len(fake.spoken[0]) <= 60
    assert "#" not in fake.spoken[0] and "**" not in fake.spoken[0]


# ── /voice/chat fallbacks: never crash, always reply with text ────────────────

@pytest.mark.parametrize("transcript", ["", "   ", "...", "?!"])
def test_empty_transcript_skips_llm_and_memory(make_client, transcript):
    client, llm = make_client(FakeVoice(transcript=transcript))
    body = send_voice(client).json()

    assert body["fallback_reason"] == "empty_transcript"
    assert body["audio_b64"] is None
    assert llm.calls == 0
    assert client.get("/memory/1").json()["total_messages"] == 0


@pytest.mark.parametrize("reason", ["auth", "plan_limit", "rate_limited", "timeout", "unavailable"])
def test_stt_failure_falls_back_to_text(make_client, reason):
    client, llm = make_client(FakeVoice(stt_error=reason))
    r = send_voice(client)
    assert r.status_code == 200
    assert r.json()["fallback_reason"] == "stt_failed"
    assert llm.calls == 0


def test_voice_disabled_says_so(make_client):
    client, llm = make_client(FakeVoice(stt_error="disabled"))
    body = send_voice(client).json()
    assert body["fallback_reason"] == "voice_disabled"
    assert "turned off" in body["response"]


def test_tts_failure_still_returns_full_text_reply(make_client):
    client, llm = make_client(FakeVoice(transcript="Hi", tts_error="plan_limit"))
    r = send_voice(client)
    body = r.json()
    assert r.status_code == 200
    assert body["response"] == "reply to: Hi"
    assert body["audio_b64"] is None
    assert body["fallback_reason"] == "tts_failed"
    # the conversation still happened and was remembered
    assert client.get("/memory/1").json()["total_messages"] == 2


def test_llm_failure_is_502_like_text_chat(make_client):
    client, llm = make_client(FakeVoice(transcript="Hi"))

    async def broken_chat(messages, system):
        raise RuntimeError("LLM down")

    llm.chat = broken_chat
    assert send_voice(client).status_code == 502


# ── Metrics: one JSON line per voice turn ──────────────────────────────────────

def read_metrics(tmp_path):
    path = tmp_path / "metrics.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_voice_turn_writes_one_metrics_line(make_client, tmp_path):
    client, llm = make_client(FakeVoice(transcript="How do rockets work?"), reply=LONG_STRUCTURED_REPLY)
    client.post(
        "/voice/chat",
        data={"chat_id": "1", "duration_s": "4.2"},
        files={"audio": ("note.ogg", b"OggS-fake-note", "audio/ogg")},
    )
    [row] = read_metrics(tmp_path)
    assert row["audio_seconds"] == 4.2
    assert row["spoken_by"] == "summary"
    assert row["pre_cap_chars"] >= row["spoken_chars"] > 0
    assert set(row["timings_ms"]) == {"stt", "llm", "summary", "tts", "total"}
    assert "How do rockets work?" not in json.dumps(row)   # numbers only, never transcripts


@pytest.mark.parametrize("fake, expected", [
    (FakeVoice(transcript="..."), "empty_transcript"),
    (FakeVoice(stt_error="auth"), "stt_failed"),
    (FakeVoice(transcript="Hi", tts_error="plan_limit"), "tts_failed"),
])
def test_fallbacks_are_recorded_too(make_client, tmp_path, fake, expected):
    client, llm = make_client(fake)
    send_voice(client)
    assert read_metrics(tmp_path)[-1]["fallback"] == expected


def test_llm_failure_is_recorded_then_502(make_client, tmp_path):
    client, llm = make_client(FakeVoice(transcript="Hi"))

    async def broken_chat(messages, system):
        raise RuntimeError("LLM down")

    llm.chat = broken_chat
    assert send_voice(client).status_code == 502
    assert read_metrics(tmp_path)[-1]["fallback"] == "llm_failed"


def test_metrics_write_failure_does_not_break_the_turn(make_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "voice_metrics_path", str(tmp_path / "missing-dir" / "m.jsonl"))
    client, llm = make_client()
    r = send_voice(client)
    assert r.status_code == 200 and r.json()["audio_b64"] is not None


# ── Output limits ──────────────────────────────────────────────────────────────

def test_cut_main_answer_is_recorded(make_client, tmp_path):
    client, llm = make_client(FakeVoice(transcript="History of Rome?"), reply=LONG_STRUCTURED_REPLY + OUTPUT_LIMIT_NOTICE)
    body = send_voice(client).json()
    assert body["llm_cut"] is True
    assert read_metrics(tmp_path)[-1]["llm_cut"] is True


def test_speech_model_cut_off_is_never_spoken(make_client):
    # If Haiku itself runs out of tokens, the voice drops the half sentence and the notice
    speech_llm = FakeLLM("Rockets push gas down. The gas pushes the roc" + OUTPUT_LIMIT_NOTICE)
    fake = FakeVoice(transcript="How do rockets work?")
    client, llm = make_client(fake, reply=LONG_STRUCTURED_REPLY, speech_llm=speech_llm)
    body = send_voice(client).json()
    assert fake.spoken[0] == "Rockets push gas down."
    assert body["spoken_by"] == "summary"
