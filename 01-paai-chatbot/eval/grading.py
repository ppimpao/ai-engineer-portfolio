"""
Grading for eval cases: compare an output (and facts about how it was produced)
against a case's expectations. Pure functions, unit-tested in tests/test_grading.py.

Supported checks (all optional, all case-insensitive for text):
    expected_contains   every string must appear
    expected_any        at least one string must appear
    must_not_contain    no string may appear
    expected_language   facts["language"] must be one of these
    expected_fallback   facts["fallback"] must equal this
    max_llm_calls       facts["llm_calls"] must be at most this
    expected_spoken_by  facts["spoken_by"] must equal this
    max_chars           the output must be at most this long
    ends_with_sentence  the output must end with . ! or ? (not cut mid-sentence)
    no_markdown         the output must contain no Markdown symbols
"""

import re

_MARKDOWN = re.compile(r"\*\*|`|^\s*#|\]\(|^\s*[-*+]\s|\|", re.MULTILINE)


def grade(case: dict, output: str, facts: dict | None = None) -> list[str]:
    """Return a list of failure messages; an empty list means the case passed."""
    facts = facts or {}
    text = output.lower()
    failures = []

    for expected in case.get("expected_contains", []):
        if expected.lower() not in text:
            failures.append(f"missing expected string: '{expected}'")

    options = case.get("expected_any", [])
    if options and not any(o.lower() in text for o in options):
        failures.append(f"none of the acceptable strings present: {options}")

    for forbidden in case.get("must_not_contain", []):
        if forbidden.lower() in text:
            failures.append(f"contains forbidden string: '{forbidden}'")

    if "expected_language" in case and facts.get("language") not in case["expected_language"]:
        failures.append(f"language {facts.get('language')!r} not in {case['expected_language']}")

    if "expected_fallback" in case and facts.get("fallback") != case["expected_fallback"]:
        failures.append(f"fallback {facts.get('fallback')!r}, expected {case['expected_fallback']!r}")

    if "max_llm_calls" in case and facts.get("llm_calls", 0) > case["max_llm_calls"]:
        failures.append(f"LLM called {facts.get('llm_calls')} time(s), allowed {case['max_llm_calls']}")

    if "expected_spoken_by" in case and facts.get("spoken_by") != case["expected_spoken_by"]:
        failures.append(f"spoken_by {facts.get('spoken_by')!r}, expected {case['expected_spoken_by']!r}")

    if "max_chars" in case and len(output) > case["max_chars"]:
        failures.append(f"{len(output)} chars, limit {case['max_chars']}")

    if case.get("ends_with_sentence") and not output.rstrip().endswith((".", "!", "?")):
        failures.append(f"does not end with a complete sentence: '…{output.rstrip()[-30:]}'")

    if case.get("no_markdown") and _MARKDOWN.search(output):
        failures.append(f"contains Markdown: '{_MARKDOWN.search(output).group()}'")

    return failures
