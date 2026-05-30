from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.llm.factory import get_llm_provider
from core.memory.database import init_db
from core.memory.manager import MemoryManager

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path("prompts/system.txt").read_text(encoding="utf-8")

provider = get_llm_provider()
memory = MemoryManager(provider)


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


class MemoryStatsResponse(BaseModel):
    total_messages: int
    total_tokens_stored: int
    messages_in_context: int
    tokens_in_context: int
    context_budget: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    text = req.text.strip()

    # Guard: never forward empty/whitespace-only input to the LLM.
    if not text:
        return ChatResponse(
            response="It looks like your message was empty. What would you like to ask?",
            tokens_in_context=0,
        )

    logger.info("chat_id=%d | user: %s", req.chat_id, text[:80])

    await memory.add_message(req.chat_id, "user", text)

    context, token_count = await memory.get_context(req.chat_id)

    try:
        reply = await provider.chat(messages=context, system=SYSTEM_PROMPT)
    except Exception as e:
        logger.error("LLM error for chat_id=%d: %s", req.chat_id, e)
        raise HTTPException(status_code=502, detail="The AI backend is unavailable. Please try again.")

    await memory.add_message(req.chat_id, "assistant", reply)

    logger.info("chat_id=%d | assistant: %s", req.chat_id, reply[:80])
    return ChatResponse(response=reply, tokens_in_context=token_count)


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
    return {"status": "ok", "provider": settings.llm_provider, "model": settings.claude_model}
