#!/usr/bin/env python3
"""Build the Lina in Berlin HTML reader."""

import html
import json
import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent
IMAGES_DIR = BASE / "images"
AUDIO_DIR = BASE / "audio"
SITE_DIR = BASE / "site"
SITE_DIR.mkdir(exist_ok=True)
(SITE_DIR / "images").mkdir(exist_ok=True)
(SITE_DIR / "audio").mkdir(exist_ok=True)

story = json.loads((BASE / "story.json").read_text())


def copy_asset(src_dir, filename):
    src = src_dir / filename
    if src.exists():
        folder = "images" if src.suffix == ".png" else "audio"
        dest = SITE_DIR / folder / src.name
        shutil.copy2(src, dest)
        return f"{folder}/{src.name}"
    return None


def escape(text):
    return html.escape(text, quote=False)


def normalize_glossary(items):
    glossary = []
    for item in items or []:
        if isinstance(item, dict):
            term = item["term"]
            translation = item["translation"]
            matches = item.get("matches") or [term]
        else:
            term, translation = item
            matches = [term]
        seen = set()
        ordered_matches = []
        for match in matches:
            key = match.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered_matches.append(match)
        glossary.append({
            "term": term,
            "translation": translation,
            "matches": ordered_matches,
        })
    return glossary


def wrap_terms(text, glossary):
    if not text:
        return "", set()
    plain = escape(text).replace("\n", "<br>")
    if not glossary:
        return plain, set()

    variants = []
    lookup = {}
    for entry in glossary:
        for match in entry["matches"]:
            key = match.casefold()
            if key in lookup:
                continue
            lookup[key] = entry
            variants.append(match)

    if not variants:
        return plain, set()

    pattern = re.compile(
        rf"(?<![\w-])({'|'.join(re.escape(match) for match in sorted(variants, key=len, reverse=True))})(?![\w-])",
        re.IGNORECASE,
    )

    parts = []
    last = 0
    matched_terms = set()
    for hit in pattern.finditer(text):
        matched_text = hit.group(0)
        entry = lookup[matched_text.casefold()]
        parts.append(escape(text[last:hit.start()]))
        lemma_attr = ""
        if entry["term"].casefold() != matched_text.casefold():
            lemma_attr = f' data-lemma="{escape(entry["term"])}"'
        parts.append(
            f'<button class="tap-word" data-term="{escape(matched_text)}"{lemma_attr} '
            f'data-translation="{escape(entry["translation"])}">{escape(matched_text)}</button>'
        )
        matched_terms.add(entry["term"])
        last = hit.end()
    parts.append(escape(text[last:]))
    return "".join(parts).replace("\n", "<br>"), matched_terms


def glossary_html(glossary):
    if not glossary:
        return ""
    chips = []
    for entry in glossary:
        chips.append(
            f'<button class="vocab" type="button" data-term="{escape(entry["term"])}" '
            f'data-translation="{escape(entry["translation"])}"><strong>{escape(entry["term"])}</strong> — {escape(entry["translation"])}</button>'
        )
    return "<div class='glossary'>" + "".join(chips) + "</div>"


def interaction_html(page_index, glossary):
    if not glossary:
        return ""
    hint = '<div class="glossary-hint">Tap any highlighted German word or vocab pill for an instant translation.</div>'
    translator = (
        f'<div class="translator" id="translator-{page_index}">'
        "Tap a highlighted word or vocab pill."
        "</div>"
    )
    return hint + translator


def warn_unmatched_terms(page_id, glossary, matched_terms):
    missing = [entry["term"] for entry in glossary if entry["term"] not in matched_terms]
    if missing:
        print(f"[warn] {page_id}: glossary terms not highlighted: {', '.join(missing)}")


story_page_total = sum(1 for page in story["pages"] if page["type"] == "page")
story_page_number = 0
pages_html = []

for idx, page in enumerate(story["pages"]):
    pid = page["id"]
    image_name = page.get("image_file", f"{pid}.png")
    img = copy_asset(IMAGES_DIR, image_name)
    audio = copy_asset(AUDIO_DIR, f"{pid}.ogg")
    glossary = normalize_glossary(page.get("glossary", []))
    text_html, matched_terms = wrap_terms(page.get("text"), glossary)
    gloss = glossary_html(glossary)
    interaction = interaction_html(idx + 1, glossary)
    warn_unmatched_terms(pid, glossary, matched_terms)

    if page["type"] == "cover":
        pages_html.append(f'''
        <section class="page cover active" id="page-{idx+1}">
          <div class="cover-card">
            {f'<img src="{img}" alt="Cover" class="cover-img">' if img else '<div class="placeholder">✦</div>'}
            <div class="cover-overlay">
              <h1>{escape(story["title"])}</h1>
              <p>{escape(story["subtitle"])}</p>
            </div>
          </div>
        </section>
        ''')
        continue

    if page["type"] == "end":
        pages_html.append(f'''
        <section class="page end" id="page-{idx+1}">
          <div class="page-card end-card">
            {f'<img src="{img}" alt="Ending illustration" class="page-img full">' if img else '<div class="placeholder full">✦</div>'}
            <div class="content end-content">
              <div class="page-copy">{text_html}</div>
              {gloss}
              {interaction}
              {f'<audio controls src="{audio}"></audio>' if audio else ''}
            </div>
          </div>
        </section>
        ''')
        continue

    story_page_number += 1
    image_first = story_page_number % 2 == 0
    pages_html.append(f'''
    <section class="page" id="page-{idx+1}">
      <div class="page-card {'image-first' if image_first else 'text-first'}">
        {f'<img src="{img}" alt="Illustration" class="page-img">' if img else '<div class="placeholder">✦</div>'}
        <div class="content">
          <div class="page-copy">{text_html}</div>
          {gloss}
          {interaction}
          {f'<audio controls src="{audio}"></audio>' if audio else ''}
        </div>
      </div>
      <div class="page-number">{story_page_number}/{story_page_total}</div>
    </section>
    ''')

html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(story["title"])}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap');
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: #0f1020; color: #f7f1e8; }}
    body::before {{ content: ''; position: fixed; inset: 0; background: radial-gradient(circle at 20% 10%, rgba(255,183,77,.18), transparent 25%), radial-gradient(circle at 80% 20%, rgba(100,200,255,.15), transparent 30%), linear-gradient(180deg, #18192f 0%, #0f1020 100%); z-index: -1; }}
    .wrap {{ max-width: 1080px; margin: 0 auto; padding: 20px; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
    .titleblock h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3.25rem); }}
    .titleblock p {{ margin: 6px 0 0; color: #c9c2d6; max-width: 62ch; }}
    .nav {{ display: flex; gap: 10px; align-items: center; }}
    button {{ border: 0; border-radius: 999px; padding: 10px 16px; background: #f0a94b; color: #1c1424; font-weight: 800; cursor: pointer; }}
    button:disabled {{ opacity: .4; cursor: default; }}
    .dots {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 18px 0 22px; }}
    .dot {{ width: 11px; height: 11px; border-radius: 50%; background: rgba(255,255,255,.2); cursor: pointer; }}
    .dot.active {{ background: #f0a94b; transform: scale(1.2); }}
    .page {{ display: none; }}
    .page.active {{ display: block; }}
    .cover-card, .page-card {{ overflow: hidden; border-radius: 28px; background: rgba(255,255,255,.08); backdrop-filter: blur(10px); box-shadow: 0 18px 60px rgba(0,0,0,.3); }}
    .cover-card {{ position: relative; min-height: 74vh; }}
    .cover-img, .page-img {{ width: 100%; display: block; object-fit: cover; }}
    .cover-img {{ height: 74vh; }}
    .cover-overlay {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: end; padding: 32px; background: linear-gradient(180deg, transparent 35%, rgba(0,0,0,.74)); }}
    .cover-overlay h1 {{ margin: 0; font-size: clamp(2.4rem, 7vw, 5rem); }}
    .cover-overlay p {{ margin: 10px 0 0; font-size: 1.1rem; color: #f7e8d1; max-width: 58ch; }}
    .page-card {{ display: grid; grid-template-columns: 1fr 1fr; min-height: 68vh; }}
    .page-card.image-first .page-img {{ order: 0; }}
    .page-card.image-first .content {{ order: 1; }}
    .page-card.text-first .page-img {{ order: 1; }}
    .page-card.text-first .content {{ order: 0; }}
    .page-img {{ height: 100%; min-height: 460px; }}
    .content {{ padding: 34px; display: flex; flex-direction: column; justify-content: center; gap: 14px; background: rgba(16,16,30,.92); }}
    .page-copy {{ margin: 0; font-size: clamp(1.05rem, 2vw, 1.3rem); line-height: 1.8; }}
    .tap-word {{ background: none; border: 0; padding: 0; color: #ffcf8f; font: inherit; cursor: pointer; text-decoration: underline dotted; text-underline-offset: 3px; }}
    .tap-word.active {{ color: #fff; text-shadow: 0 0 12px rgba(240,169,75,.45); }}
    .glossary {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .vocab {{ display: inline-flex; gap: 6px; align-items: center; padding: 8px 10px; border-radius: 999px; background: rgba(255,255,255,.08); color: #f4ddbf; font-size: .92rem; cursor: pointer; border: 0; }}
    .vocab.active {{ background: rgba(240,169,75,.22); color: #fff; }}
    .glossary-hint {{ font-size: .9rem; color: #bdb3c8; margin-top: 4px; }}
    .translator {{ margin-top: 10px; border-radius: 18px; padding: 14px 16px; background: rgba(255,255,255,.06); color: #f7e8d1; min-height: 52px; }}
    .translator strong {{ color: #fff; }}
    .lemma-note {{ color: #c9c2d6; font-size: .92rem; }}
    audio {{ width: 100%; margin-top: 8px; }}
    .page-number {{ margin: 10px 8px 0; color: #b2a7bf; font-size: .9rem; text-align: right; }}
    .placeholder {{ min-height: 460px; display: grid; place-items: center; font-size: 4rem; background: linear-gradient(135deg, #2a2948, #111123); }}
    .full {{ height: 50vh; }}
    .end-content {{ text-align: center; padding: 34px; }}
    .end-content p:first-child {{ font-weight: 800; letter-spacing: .02em; }}
    @media (max-width: 860px) {{
      .page-card {{ grid-template-columns: 1fr; }}
      .page-card .page-img {{ order: 0 !important; height: 36vh; min-height: 280px; }}
      .content {{ order: 1 !important; }}
      .cover-card, .cover-img {{ min-height: 62vh; height: 62vh; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="titleblock">
        <h1>{escape(story["title"])}</h1>
        <p>{escape(story["subtitle"])}</p>
      </div>
      <div class="nav">
        <button id="prev" onclick="go(-1)">← Back</button>
        <button id="next" onclick="go(1)">Next →</button>
      </div>
    </div>

    <div class="dots">{''.join(f'<div class="dot{" active" if i == 0 else ""}" onclick="show({i+1})"></div>' for i in range(len(story["pages"])))}</div>

    {''.join(pages_html)}
  </div>

  <script>
    let current = 1;
    const total = {len(story["pages"])};

    function bind(el) {{
      el.addEventListener('click', () => {{
        document.querySelectorAll('.vocab, .tap-word').forEach((x) => x.classList.remove('active'));
        el.classList.add('active');
        const panel = document.getElementById('translator-' + current);
        if (!panel) return;
        panel.innerHTML = '';
        const head = document.createElement('strong');
        head.textContent = el.dataset.term;
        panel.append(head);
        panel.append(document.createTextNode(' — ' + el.dataset.translation));
        if (el.dataset.lemma && el.dataset.lemma !== el.dataset.term) {{
          const note = document.createElement('span');
          note.className = 'lemma-note';
          note.textContent = ' Dictionary form: ' + el.dataset.lemma;
          panel.append(note);
        }}
      }});
    }}

    function initInteractions() {{
      document.querySelectorAll('[data-term]').forEach(bind);
    }}

    function show(n) {{
      current = Math.max(1, Math.min(total, n));
      document.querySelectorAll('.page').forEach((el, i) => el.classList.toggle('active', i === current - 1));
      document.querySelectorAll('.dot').forEach((el, i) => el.classList.toggle('active', i === current - 1));
      document.getElementById('prev').disabled = current === 1;
      document.getElementById('next').disabled = current === total;
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function go(dir) {{
      show(current + dir);
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    }});

    initInteractions();
    show(1);
  </script>
</body>
</html>
'''

(SITE_DIR / "index.html").write_text(html_doc)
print(f"Built {SITE_DIR / 'index.html'}")
