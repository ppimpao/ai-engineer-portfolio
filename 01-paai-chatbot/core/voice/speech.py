"""
Turning written replies into text that sounds right when spoken.
Pure functions: no I/O, no model calls — easy to test.
"""

import re

_CODE_BLOCK = re.compile(r"```.*?(```|$)", re.DOTALL)
_HEADER_LINE = re.compile(r"^\s{0,3}#{1,6}\s", re.MULTILINE)
_LIST_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


def has_structure(text: str) -> bool:
    """True if the reply is laid out for reading: code, headers, lists or tables."""
    return bool(
        _CODE_BLOCK.search(text)
        or _HEADER_LINE.search(text)
        or len(_LIST_LINE.findall(text)) >= 2
        or _TABLE_LINE.search(text)
    )


def strip_markdown(text: str) -> str:
    """Remove Markdown symbols so text-to-speech doesn't read them aloud."""
    text = _CODE_BLOCK.sub(" ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)                     # inline code
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)       # links and images → their text
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)              # bold
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)  # *italic*
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", text)          # _italic_
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)     # headers
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)              # quotes
    text = _LIST_LINE.sub("", text)                                        # list markers
    text = re.sub(r"^\s*([-*_]\s*){3,}$", "", text, flags=re.MULTILINE)   # horizontal rules

    # One line per sentence: headers and list items have no final punctuation,
    # so add a full stop to keep them from running into the next line when spoken.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line if line[-1] in ".!?:;," else line + "." for line in lines]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def is_speakable(reply: str, max_chars: int) -> bool:
    """A reply can be spoken as-is if it's short and isn't laid out for reading."""
    return not has_structure(reply) and len(strip_markdown(reply)) <= max_chars


def drop_unfinished_sentence(text: str) -> str:
    """Trim text back to its last complete sentence (used when a model was cut off mid-sentence)."""
    end = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    return text[: end + 1] if end > 0 else text


def cap_at_sentence(text: str, max_chars: int) -> tuple[str, bool]:
    """
    Cut text to at most max_chars, at the end of a sentence when possible.
    Returns (text, was_cut).
    """
    if len(text) <= max_chars:
        return text, False
    cut = text[:max_chars]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if end >= max_chars * 0.4:  # a sentence boundary that keeps a reasonable amount
        return cut[: end + 1].strip(), True
    space = cut.rfind(" ")
    head = cut[:space] if space > 0 else cut[: max_chars - 1]  # leave room for the ellipsis
    return head.rstrip(",;:") + "…", True
