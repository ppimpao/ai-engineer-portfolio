"""
Voice smoke test: one real STT call and one real TTS call through VoiceProvider.

Usage:
    python scripts/voice_smoke.py [path/to/note.ogg]

Writes the synthesized reply to reply.ogg so it can be inspected with ffprobe
or played back. Uses a few seconds of STT and ~60 characters of TTS credit.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.voice.base import VoiceError
from core.voice.factory import get_voice_provider

DEFAULT_NOTE = "eval/audio/known_phrase.ogg"
TTS_TEXT = "Hi Pedro! Saturn is a great choice, it has the most famous rings."


async def main():
    note = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NOTE)
    if not note.exists():
        print(f"Audio file not found: {note}")
        sys.exit(1)

    provider = get_voice_provider()
    print(f"Provider: {type(provider).__name__}\n")

    try:
        start = time.perf_counter()
        transcript = await provider.transcribe(note.read_bytes(), note.name)
        stt_ms = (time.perf_counter() - start) * 1000
        print(f"STT  {stt_ms:6.0f} ms | [{transcript.language}] {transcript.text}")

        start = time.perf_counter()
        audio = await provider.synthesize(TTS_TEXT)
        tts_ms = (time.perf_counter() - start) * 1000
        Path("reply.ogg").write_bytes(audio)
        print(f"TTS  {tts_ms:6.0f} ms | {len(TTS_TEXT)} chars -> {len(audio):,} bytes "
              f"({settings.voice_output_format}) saved to reply.ogg")
    except VoiceError as e:
        print(f"Voice call failed — reason={e.reason} | {e.detail}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
