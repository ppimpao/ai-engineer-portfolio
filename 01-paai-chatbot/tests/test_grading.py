"""
Tests for eval/grading.py — the grader decides pass/fail, so it needs tests too.
(Twice in this project a wrong check, not wrong code, caused a failure.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

from grading import grade


def test_contains_is_case_insensitive():
    assert grade({"expected_contains": ["pedro", "saturn"]}, "My name is Pedro. Favorite planet: Saturn.") == []


def test_missing_word_fails():
    assert grade({"expected_contains": ["saturn"]}, "My name is Pedro.") == ["missing expected string: 'saturn'"]


def test_any_of_accepts_one_synonym():
    assert grade({"expected_any": ["newton", "thrust"]}, "It's all about thrust.") == []


def test_forbidden_code_is_caught():
    failures = grade({"must_not_contain": ["[::-1]"]}, "It uses s[::-1] to reverse it.")
    assert failures == ["contains forbidden string: '[::-1]'"]


def test_returns_in_prose_is_not_code():
    # Why voice-sum-02 forbids "def reverse" and "[::-1]" but not "return":
    # "it returns the reversed string" is a correct spoken description.
    assert grade({"must_not_contain": ["def reverse", "[::-1]"]}, "The function returns the reversed string.") == []


def test_language_and_fallback_facts():
    case = {"expected_language": ["por", "pt"], "expected_fallback": "empty_transcript", "max_llm_calls": 0}
    assert grade(case, "", {"language": "por", "fallback": "empty_transcript", "llm_calls": 0}) == []
    assert len(grade(case, "", {"language": "eng", "fallback": None, "llm_calls": 1})) == 3


def test_length_and_sentence_end():
    case = {"max_chars": 20, "ends_with_sentence": True}
    assert grade(case, "Short and done.") == []
    assert len(grade(case, "This one is far too long and also cut off…")) == 2


def test_markdown_is_detected_but_prose_dashes_are_not():
    case = {"no_markdown": True}
    assert grade(case, "Saturn - the ringed giant - is great.") == []
    for text in ["It's **bold**.", "# Title", "Use `code`.", "See [docs](url).", "- item"]:
        assert grade(case, text), text
