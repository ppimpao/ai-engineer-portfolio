import logging

import anthropic
from typing import List, Dict
from .base import LLMProvider, mark_if_cut

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def chat(self, messages: List[Dict[str, str]], system: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
        )
        hit_limit = response.stop_reason == "max_tokens"
        if hit_limit:
            logger.warning("%s reached max_tokens=%d; reply was cut", self.model, self.max_tokens)
        return mark_if_cut(response.content[0].text, hit_limit)

    def estimate_tokens(self, text: str) -> int:
        # Anthropic's rule of thumb: ~4 characters per token
        return max(1, len(text) // 4)
