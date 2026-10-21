from .base import LLMProvider
from .claude import ClaudeProvider
from .ollama import OllamaProvider
from core.config import settings


def get_llm_provider() -> LLMProvider:
    """The main model: answers every message, text or voice."""
    if settings.llm_provider == "claude":
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is not set in environment.")
        return ClaudeProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
        )
    elif settings.llm_provider == "ollama":
        return OllamaProvider(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{settings.llm_provider}'. Use 'claude' or 'ollama'.")


def get_speech_llm_provider() -> LLMProvider:
    """
    The speech model: rewrites a long or structured answer into a few spoken sentences.
    A short task with a short output, so a smaller, faster model is enough.
    """
    if settings.llm_provider == "claude":
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is not set in environment.")
        return ClaudeProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_speech_model,
            max_tokens=200,  # ~60 spoken words plus margin; the prompt sets the real limit
        )
    # Ollama: reuse the local model rather than requiring a second one
    return get_llm_provider()
