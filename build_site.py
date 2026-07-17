#!/usr/bin/env python3
"""Build the Lina in Berlin HTML reader."""

import json
import re
import shutil
import html
from pathlib import Path

BASE = Path(__file__).parent
IMAGES_DIR = BASE / "images"
AUDIO_DIR = BASE / "audio"
SITE_DIR = BASE / "site"
SITE_DIR.mkdir(exist_ok=True)
(SITE_DIR / "images").mkdir(exist_ok=True)
(SITE_DIR / "audio").mkdir(exist_ok=True)

story = json.loads((BASE / "story.json").read_text())


def copy_asset(src_dir, page_id, ext):
    src = src_dir / f"{page_id}.{ext}"
    if src.exists():
        folder = "images" if ext == "png" else "audio"
        dest = SITE_DIR / folder / f"{page_id}.{ext}"
        shutil.copy2(src, dest)
        return f"{folder}/{page_id}.{ext}"
    return None


def escape(s):
    return html.escape(s, quote=False)


def wrap_terms(text, glossary):
    if not text:
        return ""
    result = escape(text)
    if not glossary:
        return result.replace("\n", "<br>")
    # Replace longer phrases first to avoid nested partial matches.
    for german, english in sorted(glossary, key=lambda x: len(x[0]), reverse=True):
        escaped = re.escape(escape(german))
        pattern = re.compile(rf"(?<![\w-])({escaped})(?![\w-])")
        replacement = (
            f'<button class="tap-word" data-term="{escape(german)}" '
            f'data-translation="{escape(english)}">{escape(german)}</button>'
        )
        result = pattern.sub(replacement, result)
    return result.replace("\n", "<br>")


def glossary_html(items):
    if not items:
        return ""
    chips = []
    for german, english in items:
        chips.append(
            f'<button class="vocab" type="button" data-term="{escape(german)}" '
            f'data-translation="{escape(english)}"><strong>{escape(german)}</strong> — {escape(english)}</button>'
        )
    return "<div class='glossary'>" + "".join(chips) + "</div>"


pages_html = []
for idx, page in enumerate(story["pages"]):
    pid = page["id"]
    img = copy_asset(IMAGES_DIR, pid, "png")
    audio = copy_asset(AUDIO_DIR, pid, "ogg")
    text_html = wrap_terms(page.get("text"), page.get("glossary", []))
    gloss = glossary_html(page.get("glossary"))
    translator = f'<div class="translator" id="translator-{idx+1}">Tap a highlighted word.</div>'
    hint = '<div class="glossary-hint">Tap any highlighted German word or vocab pill for an instant translation.</div>'

    if page["type"] == "cover":
        pages_html.append(f'''
        <section class="page cover active" id="page-{idx+1}">
          <div class="cover-card">
            {f'<img src="{img}" alt="Cover" class="cover-img">' if img else '<div class="placeholder">✦</div>'}
            <div class="cover-overlay">
              <h1>{escape(story['title'])}</h1>
              <p>{escape(story['subtitle'])}</p>
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
              {hint}
              {translator}
              {f'<audio controls src="{audio}"></audio>' if audio else ''}
            </div>
          </div>
        </section>
        ''')
        continue

    image_first = idx % 2 == 0
    pages_html.append(f'''
    <section class="page" id="page-{idx+1}">
      <div class="page-card {'image-first' if image_first else 'text-first'}">
        {f'<img src="{img}" alt="Illustration" class="page-img">' if img else '<div class="placeholder">✦</div>'}
        <div class="content">
          <div class="page-copy">{text_html}</div>
          {gloss}
          {hint}
          {translator}
          {f'<audio controls src="{audio}"></audio>' if audio else ''}
        </div>
      </div>
      <div class="page-number">{idx}/{len(story['pages']) - 1}</div>
    </section>
    ''')

html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(story['title'])}</title>
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
    .page-copy p {{ margin: 0; font-size: clamp(1.05rem, 2vw, 1.3rem); line-height: 1.8; }}
    .tap-word {{ background: none; border: 0; padding: 0; color: #ffcf8f; font: inherit; cursor: pointer; text-decoration: underline dotted; text-underline-offset: 3px; }}
    .tap-word.active {{ color: #fff; text-shadow: 0 0 12px rgba(240,169,75,.45); }}
    .glossary {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .vocab {{ display: inline-flex; gap: 6px; align-items: center; padding: 8px 10px; border-radius: 999px; background: rgba(255,255,255,.08); color: #f4ddbf; font-size: .92rem; cursor: pointer; border: 0; }}
    .vocab.active {{ background: rgba(240,169,75,.22); color: #fff; }}
    .glossary-hint {{ font-size: .9rem; color: #bdb3c8; margin-top: 4px; }}
    .translator {{ margin-top: 10px; border-radius: 18px; padding: 14px 16px; background: rgba(255,255,255,.06); color: #f7e8d1; min-height: 52px; }}
    .translator strong {{ color: #fff; }}
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
        <h1>{escape(story['title'])}</h1>
        <p>{escape(story['subtitle'])}</p>
      </div>
      <div class="nav">
        <button id="prev" onclick="go(-1)">← Back</button>
        <button id="next" onclick="go(1)">Next →</button>
      </div>
    </div>

    <div class="dots">{''.join(f'<div class="dot{" active" if i == 0 else ""}" onclick="show({i+1})"></div>' for i in range(len(story['pages'])))}</div>

    {''.join(pages_html)}
  </div>

  <script>
    let current = 1;
    const total = {len(story['pages'])};

    function bind(el) {{
      el.addEventListener('click', () => {{
        document.querySelectorAll('.vocab, .tap-word').forEach((x) => x.classList.remove('active'));
        el.classList.add('active');
        const panel = document.getElementById('translator-' + current);
        if (panel) panel.innerHTML = '<strong>' + el.dataset.term + '</strong> — ' + el.dataset.translation;
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
    function go(dir) {{ show(current + dir); }}
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
