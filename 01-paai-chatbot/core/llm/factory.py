from .base import LLMProvider
from .claude import ClaudeProvider
from .ollama import OllamaProvider
from core.config import settings


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "claude":
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is not set in environment.")
        return ClaudeProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
        )
    elif settings.llm_provider == "ollama":
        return OllamaProvider(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{settings.llm_provider}'. Use 'claude' or 'ollama'.")
