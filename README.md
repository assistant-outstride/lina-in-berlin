# After Hours German

Static site for short illustrated German readers for adults.

## Direction

The product focus is adult, addictive, learner-friendly fiction:

- risqué but readable
- emotionally messy, not mechanically explicit
- simple enough for A1-B1 learners to keep moving
- built around tension, nightlife, desire, secrecy, and bad decisions

## Content Model

- `library.json`: published story cards for the public homepage
- `story.json` and `*.json`: page-by-page source for individual readers
- `ideas.json`: story vault and editorial brief for future concepts
- `site/admin/index.html`: browser-only JSON CMS for reviewing and editing ideas

## Build

Run:

```bash
python3 build_site.py
```

This rebuilds:

- `site/index.html`
- `site/stories/<slug>/index.html`
- `site/admin/index.html`

## Admin Workflow

The admin page is intentionally lightweight:

- it loads seeded ideas from `ideas.json`
- it lets you edit ideas in the browser
- it autosaves drafts to `localStorage`
- it can export the current state as JSON for copying back into the repo

## Default Story Workflow

For a new story or act, the default expectation is:

```bash
python3 generate_story_assets.py --story-file <story.json>
python3 build_site.py
```

That workflow should produce:

- story text source
- illustration assets
- narration audio
- rebuilt static pages
