"""
Tests for eval/voice_metrics.py — the README numbers must be computed correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

from voice_metrics import percentile, summarize


def row(spoken_by="direct", total=3000, pre_cap=100, spoken=100, cut=False, fallback=None, summary_ms=None):
    timings = {"stt": 700, "llm": 2000, "tts": 600, "total": total}
    if summary_ms:
        timings["summary"] = summary_ms
    return {"ts": "2026-10-07T10:00:00+00:00", "language": "eng", "audio_seconds": 4.0,
            "timings_ms": timings, "reply_chars": 300, "pre_cap_chars": pre_cap,
            "spoken_chars": spoken, "spoken_by": spoken_by, "cut": cut, "fallback": fallback}


def test_percentile_nearest_rank():
    values = list(range(1, 11))          # 1..10
    assert percentile(values, 50) == 5
    assert percentile(values, 90) == 9
    assert percentile([7], 90) == 7      # one sample: p90 is that sample


def test_empty_file():
    assert summarize([]) == "No voice turns recorded yet."


def test_latency_is_split_by_path():
    rows = [row(total=3000), row(total=4000),
            row("summary", total=12000, pre_cap=450, spoken=450, summary_ms=1800)]
    text = summarize(rows)
    assert "| Direct (short reply) | 2 |" in text
    assert "| Summary (long reply) | 1 |" in text
    assert "3,500 / 4,000" in text        # direct total: median 3500, p90 4000


def test_cut_count_and_fallbacks():
    rows = [row(cut=True, spoken=500), row(),
            row(spoken=0, fallback="empty_transcript")]
    text = summarize(rows)
    assert "Cut by the safety cap: **1 of 2** voiced turns." in text   # silent turn isn't "voiced"
    assert "empty_transcript × 1" in text
