"""
Unit tests for memory manager — no LLM calls, no real DB.
Uses an in-memory SQLite database via a temporary db_path override.
"""

import asyncio
import os
import pytest
import tempfile

os.environ.setdefault("TELEGRAM_TOKEN", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")


from core.config import settings


class MockProvider:
    def estimate_tokens(self, text: str) -> int:
        return len(text.split())  # word count as token proxy

    async def chat(self, messages, system):
        return "mock reply"


@pytest.fixture
def tmp_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    original = settings.db_path
    settings.db_path = db_file
    yield db_file
    settings.db_path = original


@pytest.fixture
def manager():
    from core.memory.manager import MemoryManager
    return MemoryManager(MockProvider())


@pytest.mark.asyncio
async def test_add_and_retrieve(tmp_db, manager):
    from core.memory.database import init_db
    await init_db()

    await manager.add_message(1, "user", "Hello there")
    await manager.add_message(1, "assistant", "Hi! How can I help?")

    context, tokens = await manager.get_context(1)
    assert len(context) == 2
    assert context[0]["role"] == "user"
    assert context[1]["role"] == "assistant"
    assert tokens > 0


@pytest.mark.asyncio
async def test_clear_memory(tmp_db, manager):
    from core.memory.database import init_db
    await init_db()

    await manager.add_message(2, "user", "Remember this")
    await manager.clear(2)

    context, tokens = await manager.get_context(2)
    assert context == []
    assert tokens == 0


@pytest.mark.asyncio
async def test_conversations_are_isolated(tmp_db, manager):
    from core.memory.database import init_db
    await init_db()

    await manager.add_message(10, "user", "I am user 10")
    await manager.add_message(20, "user", "I am user 20")

    ctx_10, _ = await manager.get_context(10)
    ctx_20, _ = await manager.get_context(20)

    assert len(ctx_10) == 1
    assert len(ctx_20) == 1
    assert ctx_10[0]["content"] != ctx_20[0]["content"]


@pytest.mark.asyncio
async def test_token_window_trims_oldest(tmp_db):
    from core.memory.database import init_db
    from core.memory.manager import MemoryManager

    settings.max_context_tokens = 5  # very tight budget
    manager = MemoryManager(MockProvider())
    await init_db()

    # Each message is ~3 tokens (3 words). Two messages = 6 > budget of 5.
    # Window should keep only the most recent.
    await manager.add_message(99, "user", "one two three")
    await manager.add_message(99, "assistant", "four five six")
    await manager.add_message(99, "user", "seven eight nine")

    context, _ = await manager.get_context(99)
    # Oldest message should have been trimmed
    assert context[0]["content"] != "one two three"

    settings.max_context_tokens = 4000  # restore
