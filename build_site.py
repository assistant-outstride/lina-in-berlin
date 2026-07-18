#!/usr/bin/env python3
"""Build the After Hours German library site."""

import html
import json
import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent
IMAGES_DIR = BASE / "images"
AUDIO_DIR = BASE / "audio"
SITE_DIR = BASE / "site"
LIBRARY = json.loads((BASE / "library.json").read_text())
IDEAS = json.loads((BASE / "ideas.json").read_text())


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_story_dir(slug):
    story_dir = SITE_DIR / "stories" / slug
    if story_dir.exists():
        shutil.rmtree(story_dir)
    ensure_dir(story_dir / "images")
    ensure_dir(story_dir / "audio")
    return story_dir


def escape(text):
    return html.escape(text, quote=False)


def copy_asset(src_dir, filename, dest_dir):
    src = src_dir / filename
    if src.exists():
        folder = "images" if src.suffix == ".png" else "audio"
        dest = dest_dir / folder / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return f"{folder}/{src.name}"
    return None


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


def build_story_reader(story_meta):
    story = json.loads((BASE / story_meta["data_file"]).read_text())
    story_dir = reset_story_dir(story_meta["slug"])
    paywall = story.get("paywall") or {}
    paywall_kicker = paywall.get("kicker", "Continue The Night")
    paywall_title = paywall.get("title", "Unlock the next chapter")
    paywall_body = paywall.get("body", "More scenes, more tension, and worse decisions are waiting right after this.")
    paywall_button = paywall.get("button", "Unlock for €4.99")
    paywall_link = paywall.get("link_text", "Back to story library")
    paywall_note = paywall.get("note", "Not live yet. For now it only makes sparkles.")
    story_page_total = sum(1 for page in story["pages"] if page["type"] == "page")
    story_page_number = 0
    pages_html = []

    for idx, page in enumerate(story["pages"]):
        pid = page["id"]
        image_name = page.get("image_file", f"{pid}.png")
        img = copy_asset(IMAGES_DIR, image_name, story_dir)
        audio = copy_asset(AUDIO_DIR, f"{pid}.ogg", story_dir)
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
                  <span class="eyebrow">{escape(story_meta["level"])} reader</span>
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
                  <div class="fake-paywall">
                    <span class="paywall-kicker">{escape(paywall_kicker)}</span>
                    <h2>{escape(paywall_title)}</h2>
                    <p>{escape(paywall_body)}</p>
                    <button class="paywall-button" type="button" data-paywall-button>{escape(paywall_button)}</button>
                    <div class="paywall-links">
                      <a class="paywall-link" href="../../index.html">{escape(paywall_link)}</a>
                    </div>
                    <p class="paywall-note">{escape(paywall_note)}</p>
                    <div class="sparkle-zone" aria-hidden="true"></div>
                  </div>
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
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;500;700;800&display=swap');
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Manrope, sans-serif; background: #0d1020; color: #f6efe2; }}
    body::before {{ content: ''; position: fixed; inset: 0; background: radial-gradient(circle at 18% 16%, rgba(255,164,82,.18), transparent 26%), radial-gradient(circle at 84% 22%, rgba(111,166,255,.14), transparent 34%), linear-gradient(180deg, #171b33 0%, #0d1020 100%); z-index: -1; }}
    a {{ color: inherit; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
    .titleblock h1 {{ margin: 0; font-family: Fraunces, serif; font-size: clamp(2.1rem, 5vw, 3.5rem); }}
    .titleblock p {{ margin: 8px 0 0; color: #c7bfd6; max-width: 64ch; }}
    .eyebrow {{ display: inline-block; margin-bottom: 12px; color: #ffcf93; font-size: .83rem; letter-spacing: .16em; text-transform: uppercase; }}
    .nav, .library-link {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .library-link a {{ text-decoration: none; }}
    button, .home-chip {{ border: 0; border-radius: 999px; padding: 11px 16px; background: #f1b15e; color: #1c1424; font-weight: 800; cursor: pointer; text-decoration: none; }}
    button:disabled {{ opacity: .4; cursor: default; }}
    .toggle-chip {{ display: inline-flex; align-items: center; gap: 10px; border-radius: 999px; padding: 10px 14px; background: rgba(255,255,255,.08); color: #f6efe2; font-size: .92rem; font-weight: 700; }}
    .toggle-chip button {{ padding: 6px 11px; min-width: 56px; background: rgba(255,255,255,.12); color: #f6efe2; }}
    .toggle-chip button[data-state="on"] {{ background: #f1b15e; color: #1c1424; }}
    .dots {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 18px 0 22px; }}
    .dot {{ width: 11px; height: 11px; border-radius: 50%; background: rgba(255,255,255,.2); cursor: pointer; }}
    .dot.active {{ background: #f1b15e; transform: scale(1.2); }}
    .page {{ display: none; }}
    .page.active {{ display: block; }}
    .cover-card, .page-card {{ overflow: hidden; border-radius: 32px; background: rgba(255,255,255,.08); backdrop-filter: blur(10px); box-shadow: 0 18px 60px rgba(0,0,0,.3); }}
    .cover-card {{ position: relative; min-height: 74vh; }}
    .cover-img, .page-img {{ width: 100%; display: block; object-fit: cover; }}
    .cover-img {{ height: 74vh; }}
    .cover-overlay {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: end; padding: 36px; background: linear-gradient(180deg, transparent 34%, rgba(0,0,0,.78)); }}
    .cover-overlay h1 {{ margin: 0; font-family: Fraunces, serif; font-size: clamp(2.6rem, 7vw, 5.2rem); }}
    .cover-overlay p {{ margin: 10px 0 0; font-size: 1.08rem; color: #f7e8d1; max-width: 58ch; }}
    .page-card {{ display: grid; grid-template-columns: 1fr 1fr; min-height: 68vh; }}
    .page-card.image-first .page-img {{ order: 0; }}
    .page-card.image-first .content {{ order: 1; }}
    .page-card.text-first .page-img {{ order: 1; }}
    .page-card.text-first .content {{ order: 0; }}
    .page-img {{ height: 100%; min-height: 460px; }}
    .content {{ padding: 34px; display: flex; flex-direction: column; justify-content: center; gap: 14px; background: rgba(15,18,30,.92); }}
    .page-copy {{ margin: 0; font-size: clamp(1.05rem, 2vw, 1.3rem); line-height: 1.8; }}
    .tap-word {{ background: none; border: 0; padding: 0; color: #ffd198; font: inherit; cursor: pointer; text-decoration: underline dotted; text-underline-offset: 3px; }}
    .tap-word.active {{ color: #fff; text-shadow: 0 0 12px rgba(241,177,94,.45); }}
    .glossary {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .vocab {{ display: inline-flex; gap: 6px; align-items: center; padding: 8px 10px; border-radius: 999px; background: rgba(255,255,255,.08); color: #f4ddbf; font-size: .92rem; cursor: pointer; border: 0; }}
    .vocab.active {{ background: rgba(241,177,94,.22); color: #fff; }}
    .glossary-hint {{ font-size: .9rem; color: #bdb3c8; margin-top: 4px; }}
    .translator {{ margin-top: 10px; border-radius: 18px; padding: 14px 16px; background: rgba(255,255,255,.06); color: #f7e8d1; min-height: 52px; }}
    .translator strong {{ color: #fff; }}
    .lemma-note {{ color: #c9c2d6; font-size: .92rem; }}
    audio {{ width: 100%; margin-top: 8px; }}
    .page-number {{ margin: 10px 8px 0; color: #b2a7bf; font-size: .9rem; text-align: right; }}
    .placeholder {{ min-height: 460px; display: grid; place-items: center; font-size: 4rem; background: linear-gradient(135deg, #2a2948, #111123); }}
    .full {{ height: 50vh; }}
    .end-content {{ text-align: center; padding: 34px; }}
    .fake-paywall {{ position: relative; margin-top: 22px; padding: 24px; border-radius: 28px; overflow: hidden; background: linear-gradient(145deg, rgba(255,255,255,.08), rgba(255,255,255,.03)); border: 1px solid rgba(255,255,255,.09); box-shadow: inset 0 1px 0 rgba(255,255,255,.06); }}
    .paywall-kicker {{ display: inline-block; color: #ffcf93; font-size: .78rem; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; }}
    .fake-paywall h2 {{ margin: 12px 0 8px; font-family: Fraunces, serif; font-size: clamp(1.8rem, 4vw, 2.5rem); }}
    .fake-paywall p {{ margin: 0; color: #d7ccdd; }}
    .paywall-button {{ position: relative; margin-top: 18px; padding: 13px 20px; background: linear-gradient(135deg, #ffd28e, #f1b15e); color: #1c1424; box-shadow: 0 12px 24px rgba(241,177,94,.24); }}
    .paywall-links {{ margin-top: 14px; }}
    .paywall-link {{ display: inline-flex; align-items: center; justify-content: center; padding: 10px 16px; border-radius: 999px; background: rgba(255,255,255,.08); color: #f6efe2; text-decoration: none; font-weight: 700; }}
    .paywall-note {{ margin-top: 12px !important; font-size: .92rem; color: #bfb4cb !important; }}
    .sparkle-zone {{ pointer-events: none; position: absolute; inset: 0; overflow: hidden; }}
    .sparkle {{ position: absolute; width: 10px; height: 10px; border-radius: 50%; background: radial-gradient(circle, rgba(255,244,210,1) 0%, rgba(255,211,147,.95) 45%, rgba(255,211,147,0) 72%); opacity: 0; transform: translate(-50%, -50%) scale(.2); animation: sparkle-burst .9s ease-out forwards; }}
    @keyframes sparkle-burst {{
      0% {{ opacity: 0; transform: translate(-50%, -50%) scale(.2); }}
      20% {{ opacity: 1; }}
      100% {{ opacity: 0; transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(1.35); }}
    }}
    @media (max-width: 860px) {{
      .page-card {{ grid-template-columns: 1fr; }}
      .page-card {{ min-height: auto; }}
      .page-card .page-img {{ order: 0 !important; height: auto; min-height: 0; object-fit: contain; background: rgba(8, 10, 20, .72); }}
      .placeholder {{ min-height: 280px; }}
      .content {{ order: 1 !important; }}
      .cover-card, .cover-img {{ min-height: 62vh; height: 62vh; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="titleblock">
        <span class="eyebrow">After Hours German</span>
        <h1>{escape(story["title"])}</h1>
        <p>{escape(story["subtitle"])}</p>
      </div>
      <div class="nav">
        <div class="library-link"><a class="home-chip" href="../../index.html">Story Library</a></div>
        <div class="toggle-chip">Autoplay <button id="autoplay-toggle" type="button" aria-pressed="true" data-state="on">On</button></div>
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
    const autoplayKey = 'afterHoursGerman.autoplay';
    let autoplay = true;

    function loadAutoplayPreference() {{
      const saved = window.localStorage.getItem(autoplayKey);
      autoplay = saved === null ? true : saved === 'true';
    }}

    function saveAutoplayPreference() {{
      window.localStorage.setItem(autoplayKey, autoplay ? 'true' : 'false');
    }}

    function updateAutoplayUI() {{
      const toggle = document.getElementById('autoplay-toggle');
      if (!toggle) return;
      toggle.textContent = autoplay ? 'On' : 'Off';
      toggle.dataset.state = autoplay ? 'on' : 'off';
      toggle.setAttribute('aria-pressed', autoplay ? 'true' : 'false');
    }}

    function activeAudio() {{
      return document.querySelector('.page.active audio');
    }}

    function pauseInactiveAudio() {{
      document.querySelectorAll('audio').forEach((audio) => {{
        if (!audio.closest('.page.active')) {{
          audio.pause();
        }}
      }});
    }}

    function syncAutoplay() {{
      pauseInactiveAudio();
      const audio = activeAudio();
      if (!audio) return;
      if (!autoplay) {{
        audio.pause();
        return;
      }}
      audio.currentTime = 0;
      const playAttempt = audio.play();
      if (playAttempt && typeof playAttempt.catch === 'function') {{
        playAttempt.catch(() => {{}});
      }}
    }}

    function burstSparkles(button) {{
      const card = button.closest('.fake-paywall');
      const zone = card ? card.querySelector('.sparkle-zone') : null;
      if (!zone) return;
      const buttonBox = button.getBoundingClientRect();
      const zoneBox = zone.getBoundingClientRect();
      const centerX = buttonBox.left - zoneBox.left + buttonBox.width / 2;
      const centerY = buttonBox.top - zoneBox.top + buttonBox.height / 2;
      for (let i = 0; i < 16; i += 1) {{
        const sparkle = document.createElement('span');
        const angle = (Math.PI * 2 * i) / 16;
        const distance = 26 + Math.random() * 52;
        sparkle.className = 'sparkle';
        sparkle.style.left = centerX + 'px';
        sparkle.style.top = centerY + 'px';
        sparkle.style.setProperty('--dx', Math.cos(angle) * distance + 'px');
        sparkle.style.setProperty('--dy', Math.sin(angle) * distance + 'px');
        sparkle.style.animationDelay = (Math.random() * .08).toFixed(2) + 's';
        zone.appendChild(sparkle);
        sparkle.addEventListener('animationend', () => sparkle.remove(), {{ once: true }});
      }}
    }}

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
      syncAutoplay();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function go(dir) {{
      show(current + dir);
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    }});

    document.getElementById('autoplay-toggle').addEventListener('click', () => {{
      autoplay = !autoplay;
      saveAutoplayPreference();
      updateAutoplayUI();
      syncAutoplay();
    }});

    document.querySelectorAll('[data-paywall-button]').forEach((button) => {{
      button.addEventListener('click', () => {{
        burstSparkles(button);
      }});
    }});

    loadAutoplayPreference();
    updateAutoplayUI();
    initInteractions();
    show(1);
  </script>
</body>
</html>
'''

    (story_dir / "index.html").write_text(html_doc)
    print(f"Built {story_dir / 'index.html'}")


def accent_styles(name):
    if name == "crimson":
        return {
            "glow": "rgba(255, 109, 133, .22)",
            "chip": "#ff8d9f",
            "wash": "linear-gradient(180deg, rgba(70,10,26,.08), rgba(0,0,0,.22))",
        }
    return {
        "glow": "rgba(255, 193, 109, .20)",
        "chip": "#f2bf6d",
        "wash": "linear-gradient(180deg, rgba(96,56,0,.07), rgba(0,0,0,.2))",
    }


def story_card_html(entry):
    accent = accent_styles(entry.get("accent"))
    tags = entry.get("tags") or [entry["level"], entry.get("language", "German"), entry["tone"]]
    pill = "".join(f'<span class="badge">{escape(tag)}</span>' for tag in tags)
    if entry["status"] == "published":
        href = f'stories/{entry["slug"]}/index.html'
        cover_image = entry.get("cover_image")
        if cover_image:
            art = f'<img src="{href.rsplit("/", 1)[0]}/images/{escape(cover_image)}" alt="{escape(entry["title"])} cover" class="story-art">'
        else:
            art = '<div class="story-art placeholder-art"><span>Act I Live</span></div>'
        action = f'<a class="story-link" href="{href}">Read Story</a>'
        extras = ""
    else:
        art = '<div class="story-art placeholder-art"><span>Coming Soon</span></div>'
        action = '<span class="story-link disabled">In Development</span>'
        extras = "<ul class='tease-list'>" + "".join(f"<li>{escape(line)}</li>" for line in entry.get("tease", [])) + "</ul>"

    return f'''
    <article class="story-card {'locked' if entry["status"] != "published" else ''}" style="--card-glow:{accent["glow"]}; --card-chip:{accent["chip"]}; --card-wash:{accent["wash"]};">
      <div class="story-frame">
        {art}
      </div>
      <div class="story-copy">
        <div class="story-pills">{pill}</div>
        <h2>{escape(entry["title"])}</h2>
        <p class="story-subtitle">{escape(entry["subtitle"])}</p>
        <p class="story-blurb">{escape(entry["blurb"])}</p>
        {extras}
        <div class="story-action">{action}</div>
      </div>
    </article>
    '''


def build_admin_page():
    admin_dir = ensure_dir(SITE_DIR / "admin")
    (admin_dir / "ideas.seed.json").write_text(json.dumps(IDEAS, indent=2))
    seed = json.dumps(IDEAS)
    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>After Hours German Admin</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;500;700;800&display=swap');
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Manrope, sans-serif; color: #f5ebde; background: #0a0d18; }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background:
        radial-gradient(circle at 14% 15%, rgba(255, 164, 90, .18), transparent 24%),
        radial-gradient(circle at 84% 18%, rgba(255, 111, 146, .16), transparent 32%),
        linear-gradient(180deg, #171221 0%, #0a0d18 100%);
      z-index: -2;
    }}
    body::after {{
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,.028) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.028) 1px, transparent 1px);
      background-size: 38px 38px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,.55), transparent 90%);
      pointer-events: none;
      z-index: -1;
    }}
    button, input, select, textarea {{ font: inherit; }}
    a {{ color: inherit; }}
    .wrap {{ max-width: 1380px; margin: 0 auto; padding: 24px; }}
    .topbar {{ display: flex; justify-content: space-between; gap: 18px; align-items: start; flex-wrap: wrap; margin-bottom: 20px; }}
    .eyebrow {{ display: inline-block; margin-bottom: 12px; color: #ffc98d; font-size: .8rem; letter-spacing: .18em; text-transform: uppercase; }}
    h1, h2, h3 {{ font-family: Fraunces, serif; }}
    h1 {{ margin: 0; font-size: clamp(2.6rem, 5vw, 4.6rem); line-height: .96; }}
    .topbar p {{ margin: 10px 0 0; max-width: 60ch; color: #d8c9d6; line-height: 1.7; }}
    .top-actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .top-actions a,
    .top-actions button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      background: rgba(255,255,255,.08);
      color: #f5ebde;
      text-decoration: none;
      font-weight: 800;
      cursor: pointer;
    }}
    .top-actions .primary {{ background: linear-gradient(135deg, #ffd291, #f2a85f); color: #1f1522; }}
    .status-line {{ margin-bottom: 18px; color: #cdbdd0; font-size: .95rem; }}
    .layout {{ display: grid; grid-template-columns: 340px minmax(0, 1fr); gap: 20px; align-items: start; }}
    .panel {{
      border-radius: 28px;
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.08);
      box-shadow: 0 18px 60px rgba(0,0,0,.24);
      overflow: hidden;
    }}
    .panel-head {{ padding: 22px 22px 0; }}
    .panel-head h2 {{ margin: 0; font-size: 1.7rem; }}
    .panel-head p {{ margin: 10px 0 0; color: #cdbfd1; line-height: 1.6; }}
    .stack {{ padding: 18px 18px 22px; display: grid; gap: 12px; }}
    .idea-list {{ max-height: 72vh; overflow: auto; padding-right: 4px; }}
    .idea-card {{
      width: 100%;
      text-align: left;
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 22px;
      background: rgba(255,255,255,.04);
      color: #f5ebde;
      padding: 16px;
      cursor: pointer;
    }}
    .idea-card.active {{
      background: linear-gradient(145deg, rgba(255,154,118,.18), rgba(255,255,255,.06));
      border-color: rgba(255,206,148,.35);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
    }}
    .idea-card strong {{ display: block; font-size: 1rem; }}
    .idea-card p {{ margin: 8px 0 0; color: #d2c3d4; line-height: 1.45; font-size: .92rem; }}
    .meta-row, .field-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .pill-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.08);
      color: #ffcf99;
      font-size: .78rem;
      font-weight: 800;
      letter-spacing: .04em;
      text-transform: uppercase;
    }}
    .editor {{ padding: 22px; display: grid; gap: 18px; }}
    .brief {{
      border-radius: 24px;
      padding: 18px;
      background: linear-gradient(145deg, rgba(255,255,255,.05), rgba(255,255,255,.03));
      border: 1px solid rgba(255,255,255,.08);
    }}
    .brief h3 {{ margin: 0 0 10px; font-size: 1.25rem; }}
    .brief p {{ margin: 0; color: #d4c8d7; line-height: 1.65; }}
    .brief ul {{ margin: 14px 0 0; padding-left: 18px; color: #f1dfd1; line-height: 1.65; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .toolbar button {{
      border: 0;
      border-radius: 999px;
      padding: 11px 14px;
      background: rgba(255,255,255,.08);
      color: #f5ebde;
      font-weight: 700;
      cursor: pointer;
    }}
    .toolbar .danger {{ background: rgba(255, 113, 146, .18); color: #ffd5df; }}
    .toolbar .warm {{ background: rgba(255, 204, 140, .18); color: #ffdcae; }}
    label {{ display: grid; gap: 8px; font-weight: 700; color: #f8efdf; }}
    input, select, textarea {{
      width: 100%;
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 16px;
      background: rgba(9,11,20,.72);
      color: #f5ebde;
      padding: 13px 14px;
    }}
    textarea {{ min-height: 120px; resize: vertical; line-height: 1.55; }}
    .full {{ grid-column: 1 / -1; }}
    .small-note {{ color: #bbadbf; font-size: .88rem; line-height: 1.5; }}
    .json-box {{
      width: 100%;
      min-height: 260px;
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 20px;
      background: rgba(9,11,20,.78);
      color: #d8f0ff;
      padding: 16px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: .88rem;
      line-height: 1.55;
      white-space: pre;
      overflow: auto;
    }}
    @media (max-width: 1020px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .idea-list {{ max-height: none; }}
    }}
    @media (max-width: 700px) {{
      .meta-row, .field-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div>
        <span class="eyebrow">Story Vault</span>
        <h1>After Hours German Admin</h1>
        <p>Lightweight idea CMS for adult German learner fiction. Edit ideas in the browser, keep drafts locally, and export clean JSON back into the project whenever the vault changes.</p>
      </div>
      <div class="top-actions">
        <a href="../index.html">Back to Library</a>
        <a class="primary" href="./ideas.seed.json" download>Download Seed JSON</a>
      </div>
    </div>

    <div class="status-line" id="status-line">Loading vault…</div>

    <div class="layout">
      <aside class="panel">
        <div class="panel-head">
          <h2>Ideas</h2>
          <p>Keep the heat high, the syntax simple, and the emotional stakes obvious.</p>
        </div>
        <div class="stack">
          <div class="toolbar">
            <button id="add-idea" class="warm" type="button">Add Idea</button>
            <button id="reset-seed" type="button">Reset Draft</button>
          </div>
          <div class="idea-list" id="idea-list"></div>
        </div>
      </aside>

      <main class="panel">
        <div class="editor">
          <section class="brief">
            <h3 id="brief-title"></h3>
            <p id="brief-positioning"></p>
            <div class="meta-row" style="margin-top:14px;">
              <div>
                <div class="small-note">Editorial focus</div>
                <p id="brief-focus"></p>
              </div>
              <div>
                <div class="small-note">Audience</div>
                <p id="brief-audience"></p>
              </div>
            </div>
            <ul id="brief-guardrails"></ul>
          </section>

          <div class="toolbar">
            <button id="save-draft" class="warm" type="button">Save Draft</button>
            <button id="copy-json" type="button">Copy JSON</button>
            <button id="download-json" type="button">Download Current JSON</button>
            <button id="delete-idea" class="danger" type="button">Delete Idea</button>
          </div>

          <div class="field-grid">
            <label>Title
              <input id="title" type="text">
            </label>
            <label>Slug / ID
              <input id="id" type="text">
            </label>
            <label>Status
              <select id="status">
                <option value="idea">idea</option>
                <option value="outline">outline</option>
                <option value="drafting">drafting</option>
                <option value="ready">ready</option>
              </select>
            </label>
            <label>Level
              <input id="level" type="text" placeholder="A2 or B1">
            </label>
            <label>Heat
              <select id="heat">
                <option value="medium">medium</option>
                <option value="medium-high">medium-high</option>
                <option value="high">high</option>
              </select>
            </label>
            <label>POV
              <input id="pov" type="text" placeholder="first person">
            </label>
            <label class="full">Setting
              <input id="setting" type="text">
            </label>
            <label class="full">Tone
              <input id="tone" type="text">
            </label>
            <label class="full">Hook
              <textarea id="hook"></textarea>
            </label>
            <label class="full">Premise
              <textarea id="premise"></textarea>
            </label>
            <label class="full">Tags
              <input id="tags" type="text" placeholder="comma, separated, tags">
            </label>
            <label class="full">Learner Focus
              <textarea id="learner_focus" placeholder="One item per line"></textarea>
            </label>
            <label class="full">Story Beats
              <textarea id="beats" placeholder="One beat per line"></textarea>
            </label>
            <label class="full">Notes
              <textarea id="notes"></textarea>
            </label>
          </div>

          <section>
            <h3>Live JSON</h3>
            <p class="small-note">This updates as you type. Drafts stay in this browser until you export or reset them.</p>
            <pre class="json-box" id="json-preview"></pre>
          </section>
        </div>
      </main>
    </div>
  </div>

  <script id="seed-data" type="application/json">{escape(seed)}</script>
  <script>
    const STORAGE_KEY = 'afterHoursGerman.ideaVault';
    const seedData = JSON.parse(document.getElementById('seed-data').textContent);
    const state = loadInitialState();
    let selectedIdeaId = state.ideas[0] ? state.ideas[0].id : null;

    const fields = {{
      id: document.getElementById('id'),
      title: document.getElementById('title'),
      status: document.getElementById('status'),
      level: document.getElementById('level'),
      heat: document.getElementById('heat'),
      pov: document.getElementById('pov'),
      setting: document.getElementById('setting'),
      tone: document.getElementById('tone'),
      hook: document.getElementById('hook'),
      premise: document.getElementById('premise'),
      tags: document.getElementById('tags'),
      learner_focus: document.getElementById('learner_focus'),
      beats: document.getElementById('beats'),
      notes: document.getElementById('notes')
    }};

    function clone(value) {{
      return JSON.parse(JSON.stringify(value));
    }}

    function loadInitialState() {{
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (!saved) return clone(seedData);
      try {{
        return JSON.parse(saved);
      }} catch (error) {{
        return clone(seedData);
      }}
    }}

    function saveDraft() {{
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      setStatus('Draft saved locally in this browser.');
    }}

    function setStatus(message) {{
      document.getElementById('status-line').textContent = message;
    }}

    function selectedIdea() {{
      return state.ideas.find((idea) => idea.id === selectedIdeaId) || state.ideas[0];
    }}

    function arrayFromComma(value) {{
      return value.split(',').map((item) => item.trim()).filter(Boolean);
    }}

    function arrayFromLines(value) {{
      return value.split('\\n').map((item) => item.trim()).filter(Boolean);
    }}

    function slugify(value) {{
      return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    }}

    function renderBrief() {{
      document.getElementById('brief-title').textContent = state.project.title;
      document.getElementById('brief-positioning').textContent = state.project.positioning;
      document.getElementById('brief-focus').textContent = state.project.editorial_focus;
      document.getElementById('brief-audience').textContent = state.project.audience;
      document.getElementById('brief-guardrails').innerHTML = state.project.guardrails
        .map((item) => `<li>${{escapeHtml(item)}}</li>`)
        .join('');
    }}

    function renderIdeaList() {{
      const root = document.getElementById('idea-list');
      root.innerHTML = '';
      state.ideas.forEach((idea) => {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'idea-card' + (idea.id === selectedIdeaId ? ' active' : '');
        button.innerHTML = `
          <strong>${{escapeHtml(idea.title || 'Untitled idea')}}</strong>
          <div class="pill-row">
            <span class="pill">${{escapeHtml(idea.level || 'level?')}}</span>
            <span class="pill">${{escapeHtml(idea.heat || 'heat?')}}</span>
            <span class="pill">${{escapeHtml(idea.status || 'idea')}}</span>
          </div>
          <p>${{escapeHtml(idea.hook || 'No hook yet.')}}</p>
        `;
        button.addEventListener('click', () => {{
          selectedIdeaId = idea.id;
          render();
        }});
        root.appendChild(button);
      }});
    }}

    function renderEditor() {{
      const idea = selectedIdea();
      if (!idea) return;
      fields.id.value = idea.id || '';
      fields.title.value = idea.title || '';
      fields.status.value = idea.status || 'idea';
      fields.level.value = idea.level || '';
      fields.heat.value = idea.heat || 'medium';
      fields.pov.value = idea.pov || '';
      fields.setting.value = idea.setting || '';
      fields.tone.value = idea.tone || '';
      fields.hook.value = idea.hook || '';
      fields.premise.value = idea.premise || '';
      fields.tags.value = (idea.tags || []).join(', ');
      fields.learner_focus.value = (idea.learner_focus || []).join('\\n');
      fields.beats.value = (idea.beats || []).join('\\n');
      fields.notes.value = idea.notes || '';
      updatePreview();
    }}

    function updatePreview() {{
      document.getElementById('json-preview').textContent = JSON.stringify(state, null, 2);
    }}

    function render() {{
      renderBrief();
      renderIdeaList();
      renderEditor();
      setStatus(`Editing ${{state.ideas.length}} ideas. Drafts persist in this browser.`);
    }}

    function syncCurrentIdea() {{
      const idea = selectedIdea();
      if (!idea) return;
      const previousId = idea.id;
      idea.title = fields.title.value.trim();
      idea.id = slugify(fields.id.value || fields.title.value || previousId || 'new-idea');
      idea.status = fields.status.value;
      idea.level = fields.level.value.trim();
      idea.heat = fields.heat.value;
      idea.pov = fields.pov.value.trim();
      idea.setting = fields.setting.value.trim();
      idea.tone = fields.tone.value.trim();
      idea.hook = fields.hook.value.trim();
      idea.premise = fields.premise.value.trim();
      idea.tags = arrayFromComma(fields.tags.value);
      idea.learner_focus = arrayFromLines(fields.learner_focus.value);
      idea.beats = arrayFromLines(fields.beats.value);
      idea.notes = fields.notes.value.trim();
      if (previousId !== idea.id) {{
        selectedIdeaId = idea.id;
      }}
      updatePreview();
      renderIdeaList();
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }}

    Object.values(fields).forEach((field) => {{
      field.addEventListener('input', syncCurrentIdea);
    }});

    document.getElementById('save-draft').addEventListener('click', () => {{
      saveDraft();
    }});

    document.getElementById('reset-seed').addEventListener('click', () => {{
      window.localStorage.removeItem(STORAGE_KEY);
      location.reload();
    }});

    document.getElementById('add-idea').addEventListener('click', () => {{
      const next = {{
        id: 'new-idea-' + (state.ideas.length + 1),
        title: 'New Idea',
        status: 'idea',
        level: 'A2',
        heat: 'medium',
        pov: 'first person',
        setting: '',
        tone: '',
        tags: [],
        hook: '',
        premise: '',
        learner_focus: [],
        beats: [],
        notes: ''
      }};
      state.ideas.unshift(next);
      selectedIdeaId = next.id;
      saveDraft();
      render();
    }});

    document.getElementById('delete-idea').addEventListener('click', () => {{
      if (state.ideas.length === 1) {{
        setStatus('The vault needs at least one idea.');
        return;
      }}
      const idea = selectedIdea();
      state.ideas = state.ideas.filter((entry) => entry.id !== idea.id);
      selectedIdeaId = state.ideas[0].id;
      saveDraft();
      render();
    }});

    document.getElementById('copy-json').addEventListener('click', async () => {{
      try {{
        await navigator.clipboard.writeText(JSON.stringify(state, null, 2));
        setStatus('Current JSON copied to clipboard.');
      }} catch (error) {{
        setStatus('Clipboard copy failed. Use the JSON panel below.');
      }}
    }});

    document.getElementById('download-json').addEventListener('click', () => {{
      const blob = new Blob([JSON.stringify(state, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'ideas.json';
      link.click();
      URL.revokeObjectURL(url);
      setStatus('Downloaded current JSON snapshot.');
    }});

    render();
  </script>
</body>
</html>
'''
    (admin_dir / "index.html").write_text(html_doc)
    print(f"Built {admin_dir / 'index.html'}")


def build_homepage():
    ensure_dir(SITE_DIR)
    cards = "".join(story_card_html(entry) for entry in LIBRARY["stories"])
    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(LIBRARY["title"])}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;500;700;800&display=swap');
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Manrope, sans-serif; background: #0b1020; color: #f7efe2; }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background:
        radial-gradient(circle at 12% 16%, rgba(244,167,78,.18), transparent 25%),
        radial-gradient(circle at 86% 18%, rgba(112,162,255,.16), transparent 32%),
        linear-gradient(180deg, #171b35 0%, #0b1020 100%);
      z-index: -2;
    }}
    body::after {{
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,.4), transparent 88%);
      z-index: -1;
      pointer-events: none;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 64px; }}
    .hero {{ margin-bottom: 22px; padding: 28px 0 6px; }}
    .eyebrow {{ display: inline-block; color: #ffcf94; letter-spacing: .18em; text-transform: uppercase; font-size: .8rem; margin-bottom: 14px; }}
    .hero h1 {{ margin: 0; font-family: Fraunces, serif; font-size: clamp(2.8rem, 6vw, 5rem); line-height: .98; max-width: 10ch; }}
    .hero p {{ max-width: 56ch; color: #d4cbde; font-size: 1.03rem; line-height: 1.7; margin: 12px 0 0; }}
    .hero-head {{ display: flex; justify-content: space-between; gap: 18px; align-items: start; flex-wrap: wrap; }}
    .hero-actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .hero-actions a {{ display: inline-flex; align-items: center; gap: 8px; text-decoration: none; padding: 12px 16px; border-radius: 999px; background: rgba(255,255,255,.08); color: #f7efe2; font-weight: 800; }}
    .hero-actions a.primary {{ background: linear-gradient(135deg, #ffd291, #f2a85f); color: #1a1320; }}
    .section-head {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; margin: 0 0 18px; flex-wrap: wrap; }}
    .section-head h2 {{ margin: 0; font-family: Fraunces, serif; font-size: clamp(1.8rem, 3vw, 2.6rem); }}
    .section-head p {{ margin: 0; max-width: 52ch; color: #c3b8d2; }}
    .stories {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; }}
    .story-card {{ border-radius: 30px; background: rgba(255,255,255,.06); box-shadow: 0 24px 60px rgba(0,0,0,.25); overflow: hidden; border: 1px solid rgba(255,255,255,.08); position: relative; }}
    .story-card::before {{ content: ''; position: absolute; inset: 0; background: radial-gradient(circle at 14% 14%, var(--card-glow), transparent 32%), var(--card-wash); pointer-events: none; }}
    .story-frame {{ position: relative; height: 340px; overflow: hidden; }}
    .story-art {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .placeholder-art {{ display: grid; place-items: center; font-family: Fraunces, serif; font-size: 2rem; color: #ffd7de; background:
      radial-gradient(circle at 20% 20%, rgba(255,145,167,.18), transparent 28%),
      linear-gradient(135deg, #2e1723, #120e19); }}
    .story-copy {{ position: relative; padding: 28px; }}
    .story-pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
    .badge {{ display: inline-flex; align-items: center; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,.08); color: var(--card-chip); font-size: .8rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }}
    .story-copy h2 {{ margin: 0; font-family: Fraunces, serif; font-size: 2rem; }}
    .story-subtitle {{ margin: 10px 0 0; color: #f3dcc0; font-weight: 700; }}
    .story-blurb {{ margin: 14px 0 0; color: #cec2d8; line-height: 1.7; }}
    .tease-list {{ margin: 16px 0 0; padding-left: 18px; color: #f0dde3; line-height: 1.6; }}
    .story-action {{ margin-top: 20px; }}
    .story-link {{ display: inline-flex; align-items: center; gap: 8px; text-decoration: none; padding: 12px 16px; border-radius: 999px; background: var(--card-chip); color: #1a1320; font-weight: 800; }}
    .story-link.disabled {{ background: rgba(255,255,255,.08); color: #ead6dc; }}
    @media (max-width: 920px) {{
      .stories {{ grid-template-columns: 1fr; }}
      .hero h1 {{ max-width: none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-head">
        <div>
          <span class="eyebrow">Adult German Readers</span>
          <h1>{escape(LIBRARY["title"])}</h1>
          <p>{escape(LIBRARY["subtitle"])}</p>
        </div>
        <div class="hero-actions">
          <a href="admin/index.html">Idea Vault</a>
          <a class="primary" href="admin/ideas.seed.json">Seed JSON</a>
        </div>
      </div>
    </section>

    <div class="section-head">
      <div>
        <h2>Choose a Story</h2>
        <p>{escape(LIBRARY["description"])}</p>
      </div>
    </div>

    <section class="stories">
      {cards}
    </section>
  </div>
</body>
</html>
'''

    (SITE_DIR / "index.html").write_text(html_doc)
    print(f"Built {SITE_DIR / 'index.html'}")


def main():
    ensure_dir(SITE_DIR)
    ensure_dir(SITE_DIR / "stories")
    for entry in LIBRARY["stories"]:
        if entry["status"] == "published":
            build_story_reader(entry)
    build_homepage()
    build_admin_page()


if __name__ == "__main__":
    main()
