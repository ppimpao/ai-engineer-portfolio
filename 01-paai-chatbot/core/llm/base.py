from abc import ABC, abstractmethod
from typing import List, Dict


class LLMProvider(ABC):
    """Common interface for all LLM backends."""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], system: str) -> str:
        """Send a conversation and return the assistant reply."""
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Rough token count used for context window management."""
        ...
