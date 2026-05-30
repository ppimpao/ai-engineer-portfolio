from typing import List, Dict, Tuple
from core.config import settings
from core.llm.base import LLMProvider
from . import database as db


class MemoryManager:
    """
    Manages per-conversation memory with a token-aware sliding window.

    Strategy: keep as many recent messages as fit within max_context_tokens,
    always preserving at least the last exchange (1 user + 1 assistant message).
    Oldest messages are dropped first when the budget is exceeded.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.max_tokens = settings.max_context_tokens

    async def add_message(self, chat_id: int, role: str, content: str) -> None:
        await db.ensure_conversation(chat_id)
        token_count = self.provider.estimate_tokens(content)
        await db.save_message(chat_id, role, content, token_count)

    async def get_context(self, chat_id: int) -> Tuple[List[Dict[str, str]], int]:
        """
        Return (windowed_messages, total_token_count) that fit within the budget.
        Messages are in chronological order (oldest first) as required by the API.
        """
        all_messages = await db.get_messages(chat_id)
        if not all_messages:
            return [], 0

        # Walk backwards, accumulating until we hit the token limit
        window: List[Dict] = []
        total_tokens = 0

        for msg in reversed(all_messages):
            cost = msg["token_count"]
            if total_tokens + cost > self.max_tokens and len(window) >= 2:
                break
            window.insert(0, {"role": msg["role"], "content": msg["content"]})
            total_tokens += cost

        return window, total_tokens

    async def clear(self, chat_id: int) -> None:
        await db.delete_conversation(chat_id)

    async def stats(self, chat_id: int) -> Dict:
        all_messages = await db.get_messages(chat_id)
        total_messages = len(all_messages)
        total_tokens = sum(m["token_count"] for m in all_messages)
        windowed, window_tokens = await self.get_context(chat_id)
        return {
            "total_messages": total_messages,
            "total_tokens_stored": total_tokens,
            "messages_in_context": len(windowed),
            "tokens_in_context": window_tokens,
            "context_budget": self.max_tokens,
        }
