import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.llm.base import OUTPUT_LIMIT_NOTICE
from core.llm.factory import get_llm_provider, get_speech_llm_provider
from core.memory.database import init_db
from core.memory.manager import MemoryManager
from core.voice.base import VoiceError
from core.voice.factory import get_voice_provider
from core.voice.speech import cap_at_sentence, drop_unfinished_sentence, is_speakable, strip_markdown
from prompts import SYSTEM_PROMPT, VOICE_SUMMARY_PROMPT

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

provider = get_llm_provider()
memory = MemoryManager(provider)
voice = get_voice_provider()
speech_llm = get_speech_llm_provider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialised.")
    yield


app = FastAPI(title="Telegram Chatbot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # tighten this for production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    chat_id: int
    text: str


class ChatResponse(BaseModel):
    response: str
    tokens_in_context: int


class VoiceChatResponse(BaseModel):
    transcript: str
    response: str
    audio_b64: str | None = None        # spoken reply; None means "reply with text"
    fallback_reason: str | None = None  # why there is no audio, if there isn't
    timings_ms: dict[str, int] = {}
    reply_chars: int = 0
    spoken_chars: int = 0
    spoken_by: str | None = None        # "direct" | "summary" | "truncated"
    send_text: bool = False             # True when the voice note doesn't carry the full answer
    pre_cap_chars: int = 0              # spoken length before the safety cap
    cut: bool = False                   # True if the safety cap had to shorten it
    language: str | None = None         # detected by speech-to-text
    llm_cut: bool = False               # True if the main model hit its output limit


class MemoryStatsResponse(BaseModel):
    total_messages: int
    total_tokens_stored: int
    messages_in_context: int
    tokens_in_context: int
    context_budget: int


# ── Chat turn (shared by text and voice) ───────────────────────────────────────

EMPTY_INPUT_REPLY = "It looks like your message was empty. What would you like to ask?"


async def run_chat_turn(chat_id: int, text: str) -> ChatResponse:
    """One conversation turn: persist the message, build context, ask the LLM, persist the reply."""
    text = text.strip()

    # Guard: never forward empty/whitespace-only input to the LLM.
    if not text:
        return ChatResponse(response=EMPTY_INPUT_REPLY, tokens_in_context=0)

    logger.info("chat_id=%d | user: %s", chat_id, text[:80])

    await memory.add_message(chat_id, "user", text)

    context, token_count = await memory.get_context(chat_id)

    try:
        reply = await provider.chat(messages=context, system=SYSTEM_PROMPT)
    except Exception as e:
        logger.error("LLM error for chat_id=%d: %s", chat_id, e)
        raise HTTPException(status_code=502, detail="The AI backend is unavailable. Please try again.")

    await memory.add_message(chat_id, "assistant", reply)

    logger.info("chat_id=%d | assistant: %s", chat_id, reply[:80])
    return ChatResponse(response=reply, tokens_in_context=token_count)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await run_chat_turn(req.chat_id, req.text)


# Telegram bots can download files up to 20 MB; anything larger isn't a voice note.
MAX_AUDIO_BYTES = 20 * 1024 * 1024

VOICE_DISABLED_REPLY = "Voice replies are turned off right now. Please send me a text message instead."
STT_FAILED_REPLY = "Sorry, I couldn't make out that voice note. Could you type it instead?"
AUDIO_TOO_LARGE_REPLY = "That voice note is too long for me. Could you send a shorter one?"
EMPTY_VOICE_REPLY = "I couldn't hear anything in that voice note. Could you try again?"


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


@dataclass
class SpokenReply:
    text: str            # what the voice note says
    spoken_by: str       # "direct" | "summary" | "truncated"
    pre_cap_chars: int   # length before the safety cap
    cut: bool            # True if the safety cap shortened it


async def prepare_spoken_reply(chat_id: int, question: str, reply: str) -> SpokenReply:
    """The spoken version of a reply, with the credit safety net applied. Used by /voice/chat and the voice evals."""
    text, spoken_by = await build_spoken_reply(chat_id, question, reply)
    # Safety net: credits are billed per character, whatever the model wrote.
    # pre_cap_chars shows whether the prompt kept the length down or the cap had to.
    capped, cut = cap_at_sentence(text, settings.max_tts_chars)
    return SpokenReply(text=capped, spoken_by=spoken_by, pre_cap_chars=len(text), cut=cut)


async def build_spoken_reply(chat_id: int, question: str, reply: str) -> tuple[str, str]:
    """
    Decide what the voice note says. Returns (spoken_text, spoken_by).

    - "direct":    a short, plain reply is spoken as-is (Markdown symbols removed).
    - "summary":   a long or structured reply is rewritten into a few spoken
                   sentences by the speech model; the full answer goes out as text.
    - "truncated": the speech model failed, so the reply is cut at a sentence.
    """
    if is_speakable(reply, settings.speak_direct_max_chars):
        return strip_markdown(reply), "direct"
    try:
        summary = await speech_llm.chat(
            messages=[{"role": "user", "content": f"User's question:\n{question}\n\nWritten answer:\n{reply}"}],
            system=VOICE_SUMMARY_PROMPT,
        )
        if summary.endswith(OUTPUT_LIMIT_NOTICE):
            # The speech model ran out of tokens: the notice is for readers, not for the voice.
            logger.warning("chat_id=%d | speech model hit its output limit", chat_id)
            summary = drop_unfinished_sentence(summary[: -len(OUTPUT_LIMIT_NOTICE)])
        if summary.strip():
            return strip_markdown(summary), "summary"
        logger.warning("chat_id=%d | speech model returned nothing, truncating", chat_id)
    except Exception as e:
        logger.warning("chat_id=%d | speech model failed, truncating | %s", chat_id, e)
    return strip_markdown(reply), "truncated"


def record_voice_metrics(result: VoiceChatResponse, audio_seconds: float, audio_bytes: int) -> None:
    """
    Append one line per voice turn to VOICE_METRICS_PATH (numbers only, never transcripts).
    Summarised by eval/voice_metrics.py. A failure here must never break the turn.
    """
    if not settings.voice_metrics_path:
        return
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "language": result.language,
        "audio_seconds": round(audio_seconds, 2),
        "audio_bytes": audio_bytes,
        "timings_ms": result.timings_ms,
        "reply_chars": result.reply_chars,
        "pre_cap_chars": result.pre_cap_chars,
        "spoken_chars": result.spoken_chars,
        "spoken_by": result.spoken_by,
        "cut": result.cut,
        "llm_cut": result.llm_cut,
        "fallback": result.fallback_reason,
    }
    try:
        with open(settings.voice_metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError as e:
        logger.warning("Could not write voice metrics: %s", e)


@app.post("/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    chat_id: int = Form(...),
    audio: UploadFile = File(...),
    duration_s: float = Form(0.0),  # sent by the bot; 0 if the client doesn't know it
):
    """
    Voice turn: speech-to-text → the same chat turn as /chat → spoken version → text-to-speech.
    Every voice failure degrades to a text reply; only an LLM failure is an error (502).
    """
    data = await audio.read()
    try:
        result = await _voice_turn(chat_id, data, audio.filename or "voice.ogg")
    except HTTPException:
        record_voice_metrics(VoiceChatResponse(transcript="", response="", fallback_reason="llm_failed"),
                             duration_s, len(data))
        raise
    record_voice_metrics(result, duration_s, len(data))
    return result


async def _voice_turn(chat_id: int, data: bytes, filename: str) -> VoiceChatResponse:
    timings: dict[str, int] = {}
    turn_start = time.perf_counter()

    if len(data) > MAX_AUDIO_BYTES:
        return VoiceChatResponse(transcript="", response=AUDIO_TOO_LARGE_REPLY, fallback_reason="audio_too_large")

    # 1. Speech-to-text
    start = time.perf_counter()
    try:
        transcript = await voice.transcribe(data, filename)
    except VoiceError as e:
        logger.warning("chat_id=%d | STT failed | reason=%s | %s", chat_id, e.reason, e.detail)
        if e.reason == "disabled":
            return VoiceChatResponse(transcript="", response=VOICE_DISABLED_REPLY, fallback_reason="voice_disabled")
        return VoiceChatResponse(transcript="", response=STT_FAILED_REPLY, fallback_reason="stt_failed")
    timings["stt"] = _elapsed_ms(start)

    # Guard: silence or noise ("...", "?") must not reach the LLM or memory.
    if not any(ch.isalnum() for ch in transcript.text):
        logger.info("chat_id=%d | empty transcript, LLM not called", chat_id)
        return VoiceChatResponse(
            transcript=transcript.text, response=EMPTY_VOICE_REPLY,
            fallback_reason="empty_transcript", timings_ms=timings, language=transcript.language,
        )

    # 2. Chat turn — identical to /chat, so voice and text share one memory
    start = time.perf_counter()
    chat_result = await run_chat_turn(chat_id, transcript.text)
    timings["llm"] = _elapsed_ms(start)
    reply = chat_result.response

    # 3. What to say: the reply itself, or a spoken summary of it
    start = time.perf_counter()
    prepared = await prepare_spoken_reply(chat_id, transcript.text, reply)
    if prepared.spoken_by != "direct":
        timings["summary"] = _elapsed_ms(start)
    spoken, spoken_by, pre_cap_chars, was_cut = prepared.text, prepared.spoken_by, prepared.pre_cap_chars, prepared.cut
    send_text = spoken_by != "direct" or was_cut

    # 4. Text-to-speech
    audio_b64, fallback_reason = None, None
    start = time.perf_counter()
    try:
        audio_b64 = base64.b64encode(await voice.synthesize(spoken)).decode("ascii")
        timings["tts"] = _elapsed_ms(start)
    except VoiceError as e:
        logger.warning("chat_id=%d | TTS failed | reason=%s | %s", chat_id, e.reason, e.detail)
        fallback_reason = "tts_failed"
        spoken = ""

    timings["total"] = _elapsed_ms(turn_start)
    logger.info(
        "voice_turn chat_id=%d | lang=%s | timings_ms=%s | reply_chars=%d | spoken_chars=%d | pre_cap_chars=%d | spoken_by=%s | cut=%s | fallback=%s",
        chat_id, transcript.language, timings, len(reply), len(spoken), pre_cap_chars, spoken_by, was_cut, fallback_reason,
    )
    return VoiceChatResponse(
        transcript=transcript.text, response=reply, audio_b64=audio_b64,
        fallback_reason=fallback_reason, timings_ms=timings,
        reply_chars=len(reply), spoken_chars=len(spoken),
        spoken_by=spoken_by, send_text=send_text,
        pre_cap_chars=pre_cap_chars, cut=was_cut, language=transcript.language,
        llm_cut=reply.endswith(OUTPUT_LIMIT_NOTICE),
    )


@app.get("/memory/{chat_id}", response_model=MemoryStatsResponse)
async def memory_stats(chat_id: int):
    stats = await memory.stats(chat_id)
    return MemoryStatsResponse(**stats)


@app.delete("/memory/{chat_id}")
async def clear_memory(chat_id: int):
    await memory.clear(chat_id)
    logger.info("Memory cleared for chat_id=%d", chat_id)
    return {"detail": f"Memory cleared for chat {chat_id}."}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "model": settings.claude_model,
        "voice": type(voice).__name__,
    }
