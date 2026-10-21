"""
Tests for the LLM providers' output-limit handling — no network.
The SDK clients are replaced with fakes that return canned responses.
"""

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")

from core.llm.base import OUTPUT_LIMIT_NOTICE
from core.llm.claude import ClaudeProvider
from core.llm.ollama import OllamaProvider


def claude_with(text: str, stop_reason: str) -> ClaudeProvider:
    provider = ClaudeProvider(api_key="fake-key")

    async def create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text=text)], stop_reason=stop_reason)

    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    return provider


def ollama_with(text: str, done_reason: str) -> OllamaProvider:
    provider = OllamaProvider(host="http://localhost:11434")

    async def chat(**kwargs):
        return {"message": {"content": text}, "done_reason": done_reason}

    provider.client = SimpleNamespace(chat=chat)
    return provider


@pytest.mark.asyncio
async def test_claude_complete_answer_is_unchanged():
    reply = await claude_with("The whole answer.", "end_turn").chat([], system="")
    assert reply == "The whole answer."


@pytest.mark.asyncio
async def test_claude_cut_answer_gets_a_notice():
    # The 8 Oct metrics: 4 of 5 long answers stopped at max_tokens with no sign of it
    reply = await claude_with("The Roman Empire began in 27 BC and", "max_tokens").chat([], system="")
    assert reply.startswith("The Roman Empire began")
    assert reply.endswith(OUTPUT_LIMIT_NOTICE)


@pytest.mark.asyncio
@pytest.mark.parametrize("done_reason, cut", [("stop", False), ("length", True)])
async def test_ollama_output_limit(done_reason, cut):
    reply = await ollama_with("Some answer", done_reason).chat([], system="")
    assert reply.endswith(OUTPUT_LIMIT_NOTICE) == cut
