import asyncio
import base64
import logging
import requests
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from core.config import settings

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

API_BASE = f"http://{settings.api_host}:{settings.api_port}"


# ── Helpers ────────────────────────────────────────────────────────────────────

def call_api(endpoint: str, method: str = "POST", timeout: float = 60, **kwargs) -> dict:
    url = f"{API_BASE}{endpoint}"
    try:
        response = getattr(requests, method.lower())(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot reach the API server. Is it running?")
    except requests.exceptions.Timeout:
        raise RuntimeError("The API server took too long to answer.")
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e))
        raise RuntimeError(detail)


# ── Commands ───────────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your AI assistant. Send me a message or a voice note and I'll do my best to help.\n\n"
        "Commands:\n"
        "/help — show this message\n"
        "/clear — wipe conversation memory\n"
        "/memory — show memory usage stats"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        await asyncio.to_thread(call_api, f"/memory/{chat_id}", method="delete")
        await update.message.reply_text("Memory cleared. Starting fresh!")
    except RuntimeError as e:
        await update.message.reply_text(f"Could not clear memory: {e}")


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        stats = await asyncio.to_thread(call_api, f"/memory/{chat_id}", method="get")
        await update.message.reply_text(
            f"Memory stats:\n"
            f"• Messages stored: {stats['total_messages']}\n"
            f"• Messages in current context: {stats['messages_in_context']}\n"
            f"• Tokens in context: {stats['tokens_in_context']} / {stats['context_budget']}\n"
            f"• Total tokens stored: {stats['total_tokens_stored']}"
        )
    except RuntimeError as e:
        await update.message.reply_text(f"Could not fetch stats: {e}")


# ── Message handler ────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    text = update.message.text
    message_type = update.message.chat.type

    # In groups, only respond when explicitly mentioned
    if message_type in ("group", "supergroup"):
        if settings.bot_username not in text:
            return
        text = text.replace(settings.bot_username, "").strip()

    logger.info("chat_id=%d | type=%s | user: %s", chat_id, message_type, text[:80])

    try:
        # requests is blocking: run it in a thread so the bot keeps serving other chats
        data = await asyncio.to_thread(call_api, "/chat", json={"chat_id": chat_id, "text": text})
        await update.message.reply_text(data["response"])
    except RuntimeError as e:
        logger.error("chat_id=%d | error: %s", chat_id, e)
        await update.message.reply_text(
            "Sorry, I couldn't process your message right now. Please try again in a moment."
        )


def _seconds(duration) -> float:
    # python-telegram-bot is moving durations from int to timedelta; accept both
    return duration.total_seconds() if hasattr(duration, "total_seconds") else float(duration or 0)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    voice = update.message.voice

    # Voice notes can't contain an @mention, so groups would get a reply to every note.
    if update.message.chat.type != "private":
        return

    seconds = _seconds(voice.duration)
    logger.info("chat_id=%d | voice note: %.1fs", chat_id, seconds)

    # Checked before downloading: a long note would spend speech-to-text credits for nothing.
    if seconds > settings.max_voice_seconds:
        await update.message.reply_text(
            f"That voice note is a bit long for me. Could you keep it under "
            f"{settings.max_voice_seconds} seconds, or type your question?"
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

    try:
        audio = await (await voice.get_file()).download_as_bytearray()
        data = await asyncio.to_thread(
            call_api,
            "/voice/chat",
            data={"chat_id": chat_id, "duration_s": seconds},
            files={"audio": ("voice.ogg", bytes(audio), voice.mime_type or "audio/ogg")},
        )
    except RuntimeError as e:
        logger.error("chat_id=%d | voice error: %s", chat_id, e)
        await update.message.reply_text(
            "Sorry, I couldn't process your voice note right now. Please try again in a moment."
        )
        return

    if data.get("fallback_reason"):
        logger.info("chat_id=%d | voice fallback: %s", chat_id, data["fallback_reason"])

    if not data.get("audio_b64"):
        # Any voice failure (or voice turned off) still gets an answer, as text.
        await update.message.reply_text(data["response"])
        return

    # Voice in → voice out. The caption shows what was heard, so a misheard note is obvious.
    transcript = data["transcript"]
    caption = f"🗣 I heard: {transcript[:200]}{'…' if len(transcript) > 200 else ''}"
    await update.message.reply_voice(voice=base64.b64decode(data["audio_b64"]), caption=caption)

    # If the voice note is a summary (or was cut), send the full answer as text too.
    if data.get("send_text"):
        await update.message.reply_text(data["response"])


# ── Error handler ──────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception: %s", context.error, exc_info=context.error)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting bot (provider: %s)...", settings.llm_provider)

    app = Application.builder().token(settings.telegram_token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(error_handler)

    logger.info("Polling...")
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(poll_interval=3)
