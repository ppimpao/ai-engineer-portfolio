"""
Evaluation runner.

Usage:
    python eval/run_eval.py

Requires CLAUDE_API_KEY (or configured provider) in .env.
Each test case runs the conversation turns through the LLM and checks
the final assistant response against expected/forbidden strings.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm.factory import get_llm_provider
from prompts import SYSTEM_PROMPT


CASES_PATH = Path(__file__).parent / "cases.json"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


async def run_case(provider, case: dict) -> bool:
    turns = case["turns"]
    # Build message history up to (but not including) the last user turn,
    # then request the assistant reply for that last turn.
    messages = [{"role": t["role"], "content": t["content"]} for t in turns]

    # Last message must be from user
    if messages[-1]["role"] != "user":
        print(f"  [skip] case {case['id']}: last turn is not user")
        return True

    # Mirror the product's empty-input guard (see api.py /chat).
    # Whitespace-only input is handled by the application, never sent to the LLM.
    if not messages[-1]["content"].strip():
        reply = "It looks like your message was empty. What would you like to ask?"
    else:
        reply = await provider.chat(messages=messages, system=SYSTEM_PROMPT)
    reply_lower = reply.lower()

    passed = True
    failures = []

    # expected_contains: ALL of these must be present
    for expected in case.get("expected_contains", []):
        if expected.lower() not in reply_lower:
            failures.append(f"missing expected string: '{expected}'")
            passed = False

    # expected_any: AT LEAST ONE of these must be present (synonym matching)
    any_options = case.get("expected_any", [])
    if any_options and not any(opt.lower() in reply_lower for opt in any_options):
        failures.append(f"none of the acceptable answers present: {any_options}")
        passed = False

    for forbidden in case.get("must_not_contain", []):
        if forbidden.lower() in reply_lower:
            failures.append(f"contains forbidden string: '{forbidden}'")
            passed = False

    status = PASS if passed else FAIL
    print(f"  [{status}] {case['id']} — {case['description']}")
    if not passed:
        for f in failures:
            print(f"         ✗ {f}")
        print(f"         Reply: {reply[:200]}")

    return passed


async def main():
    cases = json.loads(CASES_PATH.read_text())
    provider = get_llm_provider()

    print(f"\nRunning {len(cases)} evaluation cases...\n")

    results = []
    for case in cases:
        try:
            result = await run_case(provider, case)
        except Exception as e:
            print(f"  [{FAIL}] {case['id']} — crashed: {e}")
            result = False
        results.append(result)

    passed = sum(results)
    total = len(results)
    print(f"\n{'─'*40}")
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
