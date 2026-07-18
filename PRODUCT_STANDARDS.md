# After Hours German Product Standards

This repo is no longer a single-story prototype. Every new story should follow the same UX, image, audio, and metadata standards so the library stays coherent as it grows.

## Reader UX

- Mobile-first navigation:
  - Keep `Story Library` and `Autoplay` in the header.
  - Keep sequential reading controls (`Back`, progress, `Next`) in a dedicated reader control area.
  - On mobile, use a sticky bottom dock for page navigation.
- Touch targets:
  - Navigation buttons should be at least `48px` high.
  - `Next` should be more visually dominant than `Back`.
- Gestures:
  - Swipe left/right can supplement navigation.
  - Swipe must never be the only way to turn pages.
  - Vertical scrolling must remain reliable and not trigger accidental page turns.
- Progress:
  - Show a readable progress label such as `Cover`, `Page 3 of 8`, `End`.
  - Tiny unlabeled dots should not be the only progress UI on mobile.
- Audio:
  - Audio should not preload for every page at once.
  - Autoplay should apply only to the active scene.

## Image Standards

- Recurring characters need a locked identity definition in story JSON.
- For stories with the same people across multiple pages, include a `characters` section with:
  - `name`
  - `identity_lock`
  - `appearance`
  - `vibe`
- Generate a whole story’s image set in one run whenever possible, not ad hoc page-by-page.
- Current budget targets:
  - Prefer `<= 1.5 MB` per image.
  - Prefer max rendered dimensions around `1600px` on the long edge unless there is a clear reason to exceed that.
- Current repo reality:
  - Many PNGs are above `2 MB`, which is acceptable short term but should be treated as debt.
- Preferred future direction:
  - Keep source art if needed, but publish optimized delivery assets.
  - Prefer WebP or high-quality JPEG delivery assets when visual quality holds up.

## Audio Standards

- Each page should have one narration file keyed to the page `id`.
- Acceptable formats:
  - `ogg`
  - `m4a`
  - `mp3`
  - `wav`
- Prefer compressed delivery formats over WAV for published stories.
- Target `<= 250 KB` per page audio file where possible.
- Audio generation should be deterministic from `audio_text` in the story JSON.

## Story Metadata Standards

- `library.json` is the public catalog source of truth.
- Each story JSON should define:
  - `title`
  - `subtitle`
  - `status`
  - `reading_level`
  - `language`
  - `summary`
  - `visual_direction`
  - `pages`
- Naming:
  - Slug, story filename, page ids, and image/audio filenames should stay aligned.
  - Do not keep placeholder names once a story is renamed.
- Page ids should be stable once published, because they anchor audio and asset filenames.

## Build and Review Workflow

- Default workflow for a story:
  1. Finalize story JSON.
  2. Generate images for the full set.
  3. Generate audio from `audio_text`.
  4. Rebuild the static site.
  5. Review mobile reader behavior and asset weight before publishing.
- The build should warn when image or audio assets exceed the repo budget targets.
- Before publishing a new story, check:
  - character consistency
  - mobile navigation
  - image loading behavior
  - audio presence and format
  - slug / filename consistency
