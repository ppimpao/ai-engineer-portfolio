from abc import ABC, abstractmethod
from typing import List, Dict

# Appended when a reply stops because it reached the output limit, so a cut-off
# answer is never presented as complete (and Claude can pick up from it next turn).
OUTPUT_LIMIT_NOTICE = "\n\n(I ran out of space here — ask me to continue if you'd like the rest.)"


def mark_if_cut(text: str, hit_limit: bool) -> str:
    return text.rstrip() + OUTPUT_LIMIT_NOTICE if hit_limit else text


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
