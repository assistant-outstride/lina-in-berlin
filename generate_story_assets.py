#!/usr/bin/env python3
"""Generate images and audio for a story, then rebuild the site."""

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent


def parse_args():
    parser = argparse.ArgumentParser(description="Generate story assets and rebuild the site.")
    parser.add_argument(
        "--story-file",
        default="story.json",
        help="Story JSON file to read, relative to the project root.",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate existing images/audio.")
    parser.add_argument("page_ids", nargs="*", help="Optional page ids to generate.")
    return parser.parse_args()


def run_step(label, cmd):
    print(f"[step] {label}")
    subprocess.run(cmd, check=True, cwd=BASE)


def main():
    args = parse_args()
    image_cmd = [sys.executable, str(BASE / "generate.py"), "--story-file", args.story_file]
    audio_cmd = [sys.executable, str(BASE / "generate_audio.py"), "--story-file", args.story_file]
    if args.force:
        image_cmd.append("--force")
        audio_cmd.append("--force")
    if args.page_ids:
        image_cmd.extend(args.page_ids)
        audio_cmd.extend(args.page_ids)

    run_step("images", image_cmd)
    run_step("audio", audio_cmd)
    run_step("site", [sys.executable, str(BASE / "build_site.py")])


if __name__ == "__main__":
    main()
