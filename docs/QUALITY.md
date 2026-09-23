# QUALITY — the 15-point review, split machine/human

Source: AttentionClaw visual-QA + slideshow checklists, viral-carousel-creator
design non-negotiables, Jumei skill-file operating habit. Rule: a slideshow
easy to create must also be easy to reject.

## Automated (8 items, `core/review.py:run_review`)

| # | Check | How |
|---|---|---|
| 1 | Hook names viewer | gate hook-quality-v1 |
| 2 | Every slide adds info | gate render-legible-v1 (no dup text) |
| 3 | Contrast | pixel band luminance < 150 |
| 4 | Safe zones | edges calmer than band |
| 5 | Claims sourced | gate evidence-fresh-v1 |
| 6 | No invented numbers | gate claim-resolved-v1 |
| 7 | Single CTA | exactly one close post-render |
| 8 | Trackable | content_id assigned |

## Human (7 items, contact sheet + `aoc_signoff`)

| # | Check |
|---|---|
| 1 | Hook matches what follows (no bait) |
| 2 | Sequence arc holds (order is load-bearing) |
| 3 | Readable in <2s at phone size |
| 4 | Visual continuity across slides |
| 5 | Caption reinforces, not repeats |
| 6 | Fictional demos marked; no fake proof |
| 7 | Verdict recorded with reason |

`aoc_signoff` refuses empty reasons and non-{approved,revise,rejected} verdicts.
A revise/reject must name the failing item — "make it better" is not a review.

## Design non-negotiables (from research)

- 1080×1920, JPG, 5–8 slides, 10–15 words/slide, hook ≤10 words
- Max 2 fonts, 3 colors; 60% whitespace; swipe cue every slide
- Text in center 1080×1520 (top 150px + bottom 250px are UI zones; bottom 20% never)
- Squint test: readable with eyes half-closed at scroll speed
- One point per slide; open loop between slides; strongest proof before CTA
