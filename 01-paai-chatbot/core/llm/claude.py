import anthropic
from typing import List, Dict
from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], system: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def estimate_tokens(self, text: str) -> int:
        # Anthropic's rule of thumb: ~4 characters per token
        return max(1, len(text) // 4)
