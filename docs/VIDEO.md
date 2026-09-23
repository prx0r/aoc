# VIDEO — strategy and engine evaluation

## Current state (this box, Linux)

Silent slideshow MP4s from carousel slides (`render/etsy.py:render_video`):
8–12s, 1080×1080, H.264, no audio, <1MB. Proven working, Etsy-compliant,
matches the listing-video research (visual-only, big subtitles, product in
first 3s). This is the video path until real footage exists.

## Tesseract by Mirage — evaluated Sep 2026, NOT adopted

What it is: free local video creative engine for AI agents (Mirage/Captions
company). Agent-native project model: keyframes, adjustment layers,
compositions, timing, sound as editable layers — no Premiere/After Effects,
no HTML/React translation. CLI + agent skills, `.tsrct` editable projects,
review-refine-render loop. 46 stars, 5 commits — very new.

Why it's interesting:
- Same loop shape as ours (brief → editable project → preview → revise → render).
- Editable project model beats our burn-in-PNGs approach for video: change
  a title or keyframe without re-rendering everything.
- Motion graphics (animated typography) would lift slideshow-to-video output.
- Free local engine aligns with our £0 doctrine.

Why not now (three blockers):
1. **macOS/Windows only — no Linux.** This box cannot run it. Adoption needs
   a Mac/Windows machine or a re-evaluated Linux build later.
2. **No footage to edit.** Tesseract edits existing media + motion graphics;
   it doesn't generate footage. Our bottleneck is product photography, not
   editing power.
3. **Immature upstream.** 46 stars, 5 commits, plugin listing "coming soon".
   Revisit in 3–6 months.

Adoption path (when unblocked): `render/video.py` backend implementing the
existing Manifest contract, gated identically, receipts unchanged. The
abstraction already exists — only the backend is missing.

## UTM discipline (stolen from their launch link)

The link that surfaced Tesseract carried
`utm_source=x&utm_medium=social&utm_campaign=tesseractsept2026&utm_ad=launch1`.
Our campaigns should do the same on every bio link: source/medium/campaign/ad
tags flow into `aoc_measure` attribution instead of guessing which creative
drove the click. See `docs/ANALYTICS.md`.
