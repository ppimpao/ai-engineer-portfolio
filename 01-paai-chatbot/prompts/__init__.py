from pathlib import Path

SYSTEM_PROMPT = (Path(__file__).parent / "system.txt").read_text(encoding="utf-8")
