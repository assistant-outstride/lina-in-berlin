#!/usr/bin/env python3
"""Generate narration audio for Lina in Berlin."""

import json
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

story = json.loads((BASE / "story.json").read_text())

for page in story["pages"]:
    text = page.get("audio_text")
    if not text:
        continue
    out = AUDIO_DIR / f"{page['id']}.ogg"
    if out.exists():
        print(f"[skip] {page['id']}")
        continue
    print(f"[gen] {page['id']}")
    subprocess.run([
        "python3",
        str(Path.home() / ".openclaw/workspace/scripts/tts/speak.py"),
        text,
        "--save",
        str(out),
    ], check=True)
