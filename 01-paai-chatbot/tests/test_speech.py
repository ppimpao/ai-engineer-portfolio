"""
Unit tests for core/voice/speech.py — pure functions, no network.
"""

import pytest

from core.voice.speech import cap_at_sentence, drop_unfinished_sentence, has_structure, is_speakable, strip_markdown


# ── strip_markdown ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("written, spoken", [
    ("Your name is **Pedro**!", "Your name is Pedro!"),
    ("Use *this* and _that_.", "Use this and that."),
    ("See [the docs](https://example.com).", "See the docs."),
    ("Run `pip install`.", "Run pip install."),
    ("# Title\nSome text.", "Title. Some text."),
    ("- one\n- two", "one. two."),
    ("1. first\n2. second", "first. second."),
    ("> quoted", "quoted."),
])
def test_strip_markdown(written, spoken):
    assert strip_markdown(written) == spoken


def test_strip_markdown_keeps_snake_case_and_math():
    assert strip_markdown("Call snake_case_name with 2 * 3 = 6.") == "Call snake_case_name with 2 * 3 = 6."


def test_strip_markdown_drops_code_blocks():
    text = "Here's the code:\n```python\nprint('hi')\n```\nThat prints hi."
    spoken = strip_markdown(text)
    assert "print('hi')" not in spoken and "```" not in spoken
    assert spoken.endswith("That prints hi.")


# ── has_structure / is_speakable ───────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "# Header\ntext",
    "- a\n- b",
    "```\ncode\n```",
    "| a | b |\n|---|---|",
])
def test_structured_text_is_detected(text):
    assert has_structure(text)


def test_single_dash_in_prose_is_not_a_list():
    assert not has_structure("Saturn - the ringed giant - is great.")


def test_short_plain_reply_is_speakable():
    assert is_speakable("Hi Pedro! Saturn is a great choice.", max_chars=350)


def test_long_reply_is_not_speakable():
    assert not is_speakable("word " * 100, max_chars=350)


def test_markdown_symbols_do_not_count_towards_length():
    # 340 characters of content plus bold markers is still short enough
    assert is_speakable("**" + "a" * 340 + "**", max_chars=350)


# ── cap_at_sentence ────────────────────────────────────────────────────────────

def test_short_text_is_not_cut():
    assert cap_at_sentence("Hello there.", 50) == ("Hello there.", False)


def test_cut_happens_at_sentence_end():
    text = "Rockets push gas down. The gas pushes the rocket up. More detail follows here."
    spoken, was_cut = cap_at_sentence(text, 60)
    assert was_cut and spoken == "Rockets push gas down. The gas pushes the rocket up."


@pytest.mark.parametrize("text", ["word " * 50, "x" * 200])
def test_cut_never_exceeds_limit(text):
    spoken, was_cut = cap_at_sentence(text, 40)
    assert was_cut and len(spoken) <= 40 and spoken.endswith("…")


# ── drop_unfinished_sentence ───────────────────────────────────────────────────

def test_unfinished_sentence_is_dropped():
    assert drop_unfinished_sentence("Rockets push gas down. The gas pushes the roc") == "Rockets push gas down."


def test_finished_text_is_unchanged():
    assert drop_unfinished_sentence("All done here.") == "All done here."
