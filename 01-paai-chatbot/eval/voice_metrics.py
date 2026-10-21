"""
Summarise voice_metrics.jsonl into Markdown tables for the README.

Usage:
    python eval/voice_metrics.py [path/to/voice_metrics.jsonl]

Cells show "median / p90". With few turns, p90 is close to the slowest turn,
so the sample size is always printed alongside.
"""

import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent.parent / "voice_metrics.jsonl"

PATHS = [("direct", "Direct (short reply)"), ("summary", "Summary (long reply)"), ("truncated", "Truncated (speech model failed)")]
STEPS = [("stt", "STT"), ("llm", "Main LLM"), ("summary", "Speech model"), ("tts", "TTS"), ("total", "Total")]


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: the smallest value with at least p% of values at or below it."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def median_p90(values: list[float]) -> str:
    if not values:
        return "—"
    return f"{statistics.median(values):,.0f} / {percentile(values, 90):,.0f}"


def summarize(rows: list[dict]) -> str:
    if not rows:
        return "No voice turns recorded yet."

    voiced = [r for r in rows if r.get("spoken_chars", 0) > 0]
    out = [f"**Voice metrics: {len(rows)} turns** ({rows[0]['ts'][:10]} → {rows[-1]['ts'][:10]})", ""]

    # Latency, split by how the spoken reply was produced
    out += ["### Latency (ms, median / p90)", "",
            "| Path | Turns | " + " | ".join(label for _, label in STEPS) + " |",
            "|---|---|" + "---|" * len(STEPS)]
    for key, label in PATHS:
        group = [r for r in voiced if r.get("spoken_by") == key]
        if group:
            cells = [median_p90([r["timings_ms"][step] for r in group if step in r["timings_ms"]]) for step, _ in STEPS]
            out.append(f"| {label} | {len(group)} | " + " | ".join(cells) + " |")
    out.append("")

    # Spoken length: is the prompt or the cap controlling it?
    summaries = [r["pre_cap_chars"] for r in voiced if r.get("spoken_by") == "summary"]
    spoken = [r["spoken_chars"] for r in voiced]
    cut = sum(1 for r in voiced if r.get("cut"))
    out += ["### Spoken length (characters)", "",
            "| | Turns | Median | p90 | Max |", "|---|---|---|---|---|"]
    if summaries:
        out.append(f"| Speech-model summary, before cap | {len(summaries)} | {statistics.median(summaries):.0f} "
                   f"| {percentile(summaries, 90):.0f} | {max(summaries)} |")
    if spoken:
        out.append(f"| Spoken (all voiced turns) | {len(spoken)} | {statistics.median(spoken):.0f} "
                   f"| {percentile(spoken, 90):.0f} | {max(spoken)} |")
    llm_cut = sum(1 for r in voiced if r.get("llm_cut"))
    out += ["", f"Cut by the safety cap: **{cut} of {len(voiced)}** voiced turns.",
            f"Main LLM hit its output limit: **{llm_cut} of {len(voiced)}** voiced turns.", ""]

    # Usage, to compare with the credits the ElevenLabs dashboard shows
    seconds = [r.get("audio_seconds", 0) for r in rows if r.get("audio_seconds")]
    out += ["### Usage", "",
            "| | Total | Per turn (median) |", "|---|---|---|",
            f"| Audio transcribed (STT) | {sum(seconds):.0f} s | {statistics.median(seconds) if seconds else 0:.1f} s |",
            f"| Characters spoken (TTS) | {sum(spoken):,} | {statistics.median(spoken) if spoken else 0:.0f} |", ""]

    # Fallbacks and languages
    fallbacks = Counter(r["fallback"] for r in rows if r.get("fallback"))
    languages = Counter(r["language"] for r in rows if r.get("language"))
    out.append("Fallbacks: " + (", ".join(f"{k} × {v}" for k, v in fallbacks.most_common()) or "none"))
    out.append("Languages: " + (", ".join(f"{k} × {v}" for k, v in languages.most_common()) or "—"))
    return "\n".join(out)


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    print(summarize(load(path)))
