#!/usr/bin/env python3
"""Generate narration audio for a structured story file."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
LEGACY_TTS = Path.home() / ".openclaw/workspace/scripts/tts/speak.py"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate narration audio.")
    parser.add_argument(
        "--story-file",
        default="story.json",
        help="Story JSON file to read, relative to the project root.",
    )
    parser.add_argument("page_ids", nargs="*", help="Specific page ids to generate.")
    parser.add_argument("--force", action="store_true", help="Regenerate audio even when files already exist.")
    return parser.parse_args()


def load_story(story_file: str):
    path = BASE / story_file
    return path, json.loads(path.read_text())


def output_path(page_id):
    if LEGACY_TTS.exists():
        return AUDIO_DIR / f"{page_id}.ogg"
    return AUDIO_DIR / f"{page_id}.wav"


def generate_with_legacy_tts(text, out):
    subprocess.run([
        "python3",
        str(LEGACY_TTS),
        text,
        "--save",
        str(out),
    ], check=True)


def generate_with_macos_tts(text, out):
    with tempfile.TemporaryDirectory() as tmpdir:
        aiff_path = Path(tmpdir) / "speech.aiff"
        subprocess.run(["/usr/bin/say", "-o", str(aiff_path), text], check=True)
        subprocess.run([
            "/usr/bin/afconvert",
            "-f",
            "WAVE",
            "-d",
            "LEI16",
            str(aiff_path),
            str(out),
        ], check=True)


def generate_audio(story, page, force=False):
    text = page.get("audio_text")
    if not text:
        return None
    out = output_path(page["id"])
    if out.exists() and not force:
        print(f"[skip] {page['id']}")
        return out
    if not LEGACY_TTS.exists():
        for stale in (
            AUDIO_DIR / f"{page['id']}.ogg",
            AUDIO_DIR / f"{page['id']}.m4a",
            AUDIO_DIR / f"{page['id']}.wav",
            AUDIO_DIR / f"{page['id']}.aiff",
        ):
            if stale.exists():
                stale.unlink()
    print(f"[gen] {page['id']}")
    if LEGACY_TTS.exists():
        generate_with_legacy_tts(text, out)
    else:
        generate_with_macos_tts(text, out)
    return out


def main():
    args = parse_args()
    story_path, story = load_story(args.story_file)
    print(f"[story] {story_path.name}")
    selected = set(args.page_ids)

    for page in story["pages"]:
        page_id = page["id"]
        if selected and page_id not in selected:
            continue
        generate_audio(story, page, force=args.force)


if __name__ == "__main__":
    main()
