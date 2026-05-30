import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from core.config import settings

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

API_BASE = f"http://{settings.api_host}:{settings.api_port}"


# ── Helpers ────────────────────────────────────────────────────────────────────

def call_api(endpoint: str, method: str = "POST", **kwargs) -> dict:
    url = f"{API_BASE}{endpoint}"
    try:
        response = getattr(requests, method.lower())(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot reach the API server. Is it running?")
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e))
        raise RuntimeError(detail)


# ── Commands ───────────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your AI assistant. Send me any message and I'll do my best to help.\n\n"
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
        call_api(f"/memory/{chat_id}", method="delete")
        await update.message.reply_text("Memory cleared. Starting fresh!")
    except RuntimeError as e:
        await update.message.reply_text(f"Could not clear memory: {e}")


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        stats = call_api(f"/memory/{chat_id}", method="get")
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
        data = call_api("/chat", json={"chat_id": chat_id, "text": text})
        await update.message.reply_text(data["response"])
    except RuntimeError as e:
        logger.error("chat_id=%d | error: %s", chat_id, e)
        await update.message.reply_text(
            "Sorry, I couldn't process your message right now. Please try again in a moment."
        )


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
    app.add_error_handler(error_handler)

    logger.info("Polling...")
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(poll_interval=3)
