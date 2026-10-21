from pathlib import Path

_DIR = Path(__file__).parent

SYSTEM_PROMPT = (_DIR / "system.txt").read_text(encoding="utf-8")
VOICE_SUMMARY_PROMPT = (_DIR / "voice_summary.txt").read_text(encoding="utf-8")
