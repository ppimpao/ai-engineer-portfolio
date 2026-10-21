"""
Voice evaluation runner: real ElevenLabs and Claude calls, fixed inputs.

Usage:
    python eval/run_voice_eval.py

Needs ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID and CLAUDE_API_KEY in .env.
Cost per full run: roughly 70-80 ElevenLabs credits and a few Haiku calls.
Uses a temporary database and writes no voice metrics, so real data is untouched.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# Must be set before the app is imported: never touch the real database or metrics.
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "voice_eval.db")
os.environ["VOICE_METRICS_PATH"] = ""

import api  # noqa: E402  (configured above)
from core.memory.database import init_db  # noqa: E402
from core.voice.null import NullVoiceProvider  # noqa: E402
from grading import grade  # noqa: E402

CASES_PATH = Path(__file__).parent / "voice_cases.json"
SILENCE = ROOT / "eval/audio/silence.ogg"
EVAL_CHAT_ID = -1  # never a real Telegram chat

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"


class SkipCase(Exception):
    pass


class CountingLLM:
    """Wraps the main model to count calls, so 'never reaches the LLM' can be checked."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def estimate_tokens(self, text):
        return self.inner.estimate_tokens(text)

    async def chat(self, messages, system):
        self.calls += 1
        return await self.inner.chat(messages, system)


def ensure_silence() -> None:
    """Generate the silent fixture with ffmpeg so anyone can reproduce it."""
    if SILENCE.exists():
        return
    if not shutil.which("ffmpeg"):
        raise SkipCase("eval/audio/silence.ogg missing and ffmpeg not installed")
    SILENCE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-t", "3", "-c:a", "libopus", str(SILENCE)],
        check=True,
    )
    print(f"  (generated {SILENCE.relative_to(ROOT)})")


def load_audio(case: dict) -> tuple[bytes, str]:
    path = ROOT / case["audio"]
    if path == SILENCE:
        ensure_silence()
    if not path.exists():
        raise SkipCase(f"{case['audio']} not found")
    return path.read_bytes(), path.name


async def run_case(case: dict, counter: CountingLLM) -> tuple[str, dict]:
    """Run one case against the real services. Returns (output text, facts)."""
    kind = case["kind"]

    if kind == "transcribe":
        audio, name = load_audio(case)
        t = await api.voice.transcribe(audio, name)
        return t.text, {"language": t.language}

    if kind == "round_trip":
        audio = await api.voice.synthesize(case["text"])
        t = await api.voice.transcribe(audio, "round_trip.ogg")
        return t.text, {"language": t.language}

    if kind == "voice_turn":
        audio, name = load_audio(case)
        counter.calls = 0
        result = await api._voice_turn(EVAL_CHAT_ID, audio, name)
        return result.response, {"fallback": result.fallback_reason, "llm_calls": counter.calls}

    if kind == "spoken_reply":
        answer = (ROOT / case["answer_file"]).read_text(encoding="utf-8")
        spoken = await api.prepare_spoken_reply(EVAL_CHAT_ID, case["question"], answer)
        return spoken.text, {"spoken_by": spoken.spoken_by, "pre_cap_chars": spoken.pre_cap_chars, "cut": spoken.cut}

    raise ValueError(f"unknown case kind: {kind}")


async def main():
    if isinstance(api.voice, NullVoiceProvider):
        print("Voice is disabled: set VOICE_PROVIDER=elevenlabs, ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.")
        sys.exit(1)

    await init_db()
    counter = CountingLLM(api.provider)
    api.provider = counter
    api.memory.provider = counter

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    print(f"\nRunning {len(cases)} voice evaluation cases...\n")

    passed = failed = skipped = 0
    for case in cases:
        start = time.perf_counter()
        try:
            output, facts = await run_case(case, counter)
        except SkipCase as e:
            print(f"  [{SKIP}] {case['id']} — {e}")
            skipped += 1
            continue
        except Exception as e:  # one broken case must not stop the others
            print(f"  [{FAIL}] {case['id']} — crashed: {type(e).__name__}: {e}")
            failed += 1
            continue

        failures = grade(case, output, facts)
        ms = (time.perf_counter() - start) * 1000
        print(f"  [{FAIL if failures else PASS}] {case['id']} — {case['description']} ({ms:,.0f} ms)")
        print(f"         → {output[:160]!r}" + (f"  {len(output)} chars" if case["kind"] == "spoken_reply" else ""))
        for f in failures:
            print(f"         ✗ {f}")
        failed += bool(failures)
        passed += not failures

    print(f"\n{'─' * 40}")
    print(f"Results: {passed}/{passed + failed} passed" + (f", {skipped} skipped" if skipped else ""))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
