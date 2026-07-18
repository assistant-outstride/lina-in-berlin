#!/usr/bin/env python3
"""Generate story illustrations from structured story metadata."""

import argparse
import base64
import json
import mimetypes
import os
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
OUT_DIR = BASE / "images"
OUT_DIR.mkdir(exist_ok=True)

DEFAULT_STYLE = (
    "Tasteful illustrated visual novella art, cinematic lighting, clean composition, expressive faces, "
    "painterly but crisp, not photorealistic, not explicit, elegant and sensual, single full-frame illustration "
    "of one story beat, no collage, no comic panels, no diptych, no triptych, no text, no page labels, no captions"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate story illustrations.")
    parser.add_argument(
        "--story-file",
        default="story.json",
        help="Story JSON file to read, relative to the project root.",
    )
    parser.add_argument("page_ids", nargs="*", help="Specific page ids to generate.")
    parser.add_argument("--force", action="store_true", help="Regenerate images even when files already exist.")
    return parser.parse_args()


def load_story(story_file: str):
    path = BASE / story_file
    return path, json.loads(path.read_text())


def flatten_lines(lines):
    if not lines:
        return ""
    if isinstance(lines, str):
        return lines.strip()
    return " ".join(str(line).strip() for line in lines if str(line).strip())


def build_character_block(story):
    characters = story.get("characters", {})
    if not characters:
        return ""

    chunks = []
    for key, character in characters.items():
        name = character.get("name", key.title())
        parts = [f"{name}: {character.get('identity_lock', '').strip()}"]
        appearance = flatten_lines(character.get("appearance", []))
        vibe = flatten_lines(character.get("vibe", ""))
        if appearance:
            parts.append(f"Appearance: {appearance}")
        if vibe:
            parts.append(f"Vibe: {vibe}")
        chunks.append(" ".join(part for part in parts if part))
    return " ".join(chunks)


def build_visual_block(story):
    visual = story.get("visual_direction", {})
    sections = [DEFAULT_STYLE]
    style = flatten_lines(visual.get("style", ""))
    scene_notes = flatten_lines(visual.get("scene_notes", []))
    character_notes = flatten_lines(visual.get("character_notes", []))
    cover_rule = flatten_lines(visual.get("cover_rule", ""))
    if style:
        sections.append(style)
    if scene_notes:
        sections.append(scene_notes)
    if character_notes:
        sections.append(character_notes)
    if cover_rule:
        sections.append(f"Cover rule: {cover_rule}")
    return " ".join(section for section in sections if section)


def build_prompt(story, page):
    blocks = [
        build_visual_block(story),
        build_character_block(story),
        flatten_lines(page.get("image_prompt", "")),
        "Keep recurring characters visually consistent with the locked character definitions in this story.",
    ]
    return " ".join(block for block in blocks if block).strip()


def output_path(page):
    return OUT_DIR / page.get("image_file", f'{page["id"]}.png')


def generate_image(story, page, force=False):
    page_id = page["id"]
    out = output_path(page)
    if out.exists() and not force:
        print(f"[skip] {page_id}")
        return out

    prompt = build_prompt(story, page)
    print(f"[gen] {page_id}")
    payload = json.dumps({
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "high",
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        mime_type = response.headers.get_content_type()
        body = response.read()

    if mime_type == "application/json":
        data = json.loads(body.decode("utf-8"))
        image_bytes = base64.b64decode(data["data"][0]["b64_json"])
    else:
        image_bytes = body
    out.write_bytes(image_bytes)
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
        if page["type"] not in {"cover", "page", "end"}:
            continue
        generate_image(story, page, force=args.force)


if __name__ == "__main__":
    main()
