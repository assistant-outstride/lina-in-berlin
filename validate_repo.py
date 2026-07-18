#!/usr/bin/env python3
"""Validate story metadata, assets, and generated site links."""

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
SITE_DIR = BASE / "site"
IMAGES_DIR = BASE / "images"
AUDIO_DIR = BASE / "audio"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
AUDIO_EXTENSIONS = {".ogg", ".m4a", ".mp3", ".wav", ".aiff"}
IMAGE_WARN_BYTES = 1_500_000
AUDIO_WARN_BYTES = 250_000
LINK_PATTERN = re.compile(r'''(?:src|href)=["']([^"']+)["']''')


def load_json(path):
    return json.loads(path.read_text())


def resolve_audio_filename(page_id, page):
    explicit = page.get("audio_file")
    if explicit:
        return explicit
    for ext in AUDIO_EXTENSIONS:
        candidate = f"{page_id}{ext}"
        if (AUDIO_DIR / candidate).exists():
            return candidate
    return f"{page_id}.ogg"


def delivery_image_name(filename):
    src = Path(filename)
    if src.suffix.lower() in IMAGE_EXTENSIONS:
        return f"{src.stem}.jpg"
    return src.name


def validate_html_links(path, errors):
    text = path.read_text()
    for ref in LINK_PATTERN.findall(text):
        if ref.startswith(("http://", "https://", "data:", "#", "mailto:", "tel:")):
            continue
        target = (path.parent / ref).resolve()
        if not target.exists():
            errors.append(f"{path.relative_to(BASE)} references missing file: {ref}")


def main():
    parser = argparse.ArgumentParser(description="Validate story metadata and generated site assets.")
    parser.add_argument("--strict-budgets", action="store_true", help="Treat asset budget overruns as errors.")
    args = parser.parse_args()

    errors = []
    warnings = []

    library = load_json(BASE / "library.json")
    stories = library.get("stories", [])

    for entry in stories:
        data_file = BASE / entry["data_file"]
        if not data_file.exists():
            errors.append(f"Missing story data file: {entry['data_file']}")
            continue

        story = load_json(data_file)
        seen_ids = set()
        for page in story.get("pages", []):
            page_id = page["id"]
            if page_id in seen_ids:
                errors.append(f"{data_file.name} has duplicate page id: {page_id}")
            seen_ids.add(page_id)

            image_name = page.get("image_file", f"{page_id}.png")
            source_image = IMAGES_DIR / image_name
            if page["type"] in {"cover", "page", "end"} and not source_image.exists():
                errors.append(f"Missing source image for {data_file.name}:{page_id}: {image_name}")
            elif source_image.exists() and source_image.stat().st_size > IMAGE_WARN_BYTES:
                warnings.append(f"Large source image {image_name}: {round(source_image.stat().st_size / 1024)} KB")

            if page.get("audio_text"):
                audio_name = resolve_audio_filename(page_id, page)
                source_audio = AUDIO_DIR / audio_name
                if not source_audio.exists():
                    errors.append(f"Missing source audio for {data_file.name}:{page_id}: {audio_name}")
                elif source_audio.stat().st_size > AUDIO_WARN_BYTES:
                    warnings.append(f"Large source audio {audio_name}: {round(source_audio.stat().st_size / 1024)} KB")

        if entry.get("status") == "published":
            site_story_dir = SITE_DIR / "stories" / entry["slug"]
            site_index = site_story_dir / "index.html"
            if not site_index.exists():
                errors.append(f"Missing built story page for published story: {entry['slug']}")
            else:
                validate_html_links(site_index, errors)

            cover_image = entry.get("cover_image")
            if cover_image:
                delivery_cover = site_story_dir / "images" / delivery_image_name(cover_image)
                if not delivery_cover.exists():
                    errors.append(f"Missing built cover image for published story {entry['slug']}: {delivery_cover.name}")

    site_index = SITE_DIR / "index.html"
    if site_index.exists():
        validate_html_links(site_index, errors)
    else:
        errors.append("Missing built site/index.html")

    for warning in warnings:
        print(f"[warn] {warning}")

    budget_errors = []
    if args.strict_budgets:
        budget_errors = [warning for warning in warnings if warning.startswith("Large ")]
        for warning in budget_errors:
            errors.append(warning.replace("Large ", "Budget exceeded: "))

    if errors:
        for error in errors:
            print(f"[error] {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
