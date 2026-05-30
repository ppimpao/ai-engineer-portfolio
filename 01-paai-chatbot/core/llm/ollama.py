from ollama import AsyncClient
from typing import List, Dict
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, host: str, model: str = "llama3.2"):
        self.client = AsyncClient(host=host)
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], system: str) -> str:
        full_messages = [{"role": "system", "content": system}] + messages
        response = await self.client.chat(model=self.model, messages=full_messages)
        return response["message"]["content"]

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
