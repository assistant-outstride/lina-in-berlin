#!/usr/bin/env python3
"""Generate illustrations for Lina in Berlin."""

import argparse
import base64
import json
import os
from pathlib import Path
from openai import OpenAI

BASE = Path(__file__).parent
OUT_DIR = BASE / "images"
OUT_DIR.mkdir(exist_ok=True)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
story = json.loads((BASE / "story.json").read_text())

STYLE = (
    "Tasteful romantic illustrated novel art, soft cinematic lighting, warm Berlin evening palette, "
    "clean composition, expressive faces, contemporary adult readers aesthetic, painterly but crisp, "
    "not photorealistic, not explicit, elegant and sensual, single full-frame illustration of one story beat, "
    "no collage, no comic panels, no diptych, no triptych, no text, no page labels, no captions"
)

CHARACTERS = (
    "Lina is an American woman in her twenties, medium-length chestnut hair, bright curious eyes, "
    "casual travel clothes, a little nervous but confident. "
    "Max is a tall German man in his twenties or early thirties, dark hair, gentle smile, clean-lined coat, "
    "calm and handsome."
)

PAGES = {
    "cover": (
        f"{STYLE}. {CHARACTERS} Book cover for 'Lina in Berlin': Lina and Max on a rainy Berlin street at night, "
        "neon reflections on wet pavement, flowers in Max's hand, warm intimacy, city lights, title space at top, "
        "romantic and atmospheric."
    ),
    "page1": (
        f"{STYLE}. {CHARACTERS} Single-scene composition: Lina beside an open laptop, smiling at Max on the call screen. "
        "Apartment interior, soft lamp light, close intimate framing, gentle anticipation."
    ),
    "page2": (
        f"{STYLE}. {CHARACTERS} Lina packing a suitcase on her bed with a red dress folded beside it. "
        "Her friend stands in the doorway looking worried and dramatic. Bright apartment, travel energy."
    ),
    "page3": (
        f"{STYLE}. {CHARACTERS} Lina sitting by airplane window above the clouds, hands on her lap, "
        "quiet nervous expression, sunrise light, travel mood, reflections in the glass."
    ),
    "page4": (
        f"{STYLE}. {CHARACTERS} Berlin airport arrival: Max waiting with flowers, Lina stepping toward him smiling. "
        "Elegant airport hall, warm reunion, emotional eye contact, cinematic composition."
    ),
    "page5": (
        f"{STYLE}. {CHARACTERS} Inside a quiet apartment at night, Lina and Max kissing softly by a window with city lights outside. "
        "Hands close, romantic tension, tasteful fade-to-black energy, no explicit detail."
    ),
    "page6": (
        f"{STYLE}. {CHARACTERS} Morning in the apartment bedroom, sunlight on white sheets, Lina sitting up and looking at a small bite mark on her collarbone, "
        "Max nearby looking innocent and a little mysterious. Soft but unsettling mood."
    ),
    "page7": (
        f"{STYLE}. {CHARACTERS} Lina holding her phone, suspicious and alert, standing in the doorway as Max watches from the hallway, "
        "subtle mystery tension, Berlin apartment, strong story-book framing."
    ),
    "end": (
        f"{STYLE}. {CHARACTERS} Closing image: Lina walking through a glowing Berlin street at dawn, city mystery ahead, "
        "small silhouette of Max in the distance, dreamy and unresolved ending, title-card feeling."
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generate story illustrations.")
    parser.add_argument("page_ids", nargs="*", help="Specific page ids to generate, like page4 or cover.")
    parser.add_argument("--force", action="store_true", help="Regenerate images even when the file already exists.")
    return parser.parse_args()


def output_path(page):
    return OUT_DIR / page.get("image_file", f'{page["id"]}.png')


def generate_image(page, prompt: str, force: bool = False):
    page_id = page["id"]
    out = output_path(page)
    if out.exists() and not force:
        print(f"[skip] {page_id}")
        return out
    print(f"[gen] {page_id}")
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="high",
        n=1,
    )
    b64 = resp.data[0].b64_json
    out.write_bytes(base64.b64decode(b64))
    return out


if __name__ == "__main__":
    args = parse_args()
    selected = set(args.page_ids)
    for page in story["pages"]:
        pid = page["id"]
        if selected and pid not in selected:
            continue
        prompt = PAGES.get(pid)
        if prompt:
            generate_image(page, prompt, force=args.force)
