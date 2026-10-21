"""
List the voices this API key can use, marking which ones work on the free plan.

Usage:
    python scripts/list_voices.py

Free plans can only use ElevenLabs' premade (default) voices through the API;
library voices return HTTP 402 "paid_plan_required". Costs no credits.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from elevenlabs.client import AsyncElevenLabs

from core.config import settings


async def main():
    client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
    response = await client.voices.get_all()

    voices = sorted(response.voices, key=lambda v: (v.category != "premade", v.name or ""))
    print(f"{'':2}{'NAME':<22}{'CATEGORY':<14}{'GENDER/ACCENT':<26}VOICE_ID")
    for v in voices:
        labels = v.labels or {}
        traits = "/".join(filter(None, [labels.get("gender"), labels.get("accent")]))
        mark = "✓ " if v.category == "premade" else "  "
        current = "  ← current" if v.voice_id == settings.elevenlabs_voice_id else ""
        print(f"{mark}{(v.name or '')[:21]:<22}{v.category or '':<14}{traits[:25]:<26}{v.voice_id}{current}")

    print("\n✓ = premade voice, usable on the free plan via the API")


if __name__ == "__main__":
    asyncio.run(main())
