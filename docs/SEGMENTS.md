# SEGMENTS — one engine, every trade as a skin

Shape stolen from `/content` gardens: the engine is generic, skins supply data.

## Rule
Engine code never names a trade. `slides/generate.py`, `core/carousel.py`,
`render/slide.py`, `core/memory.py` take a `segment` id. All trade-specific
copy lives in `segments/<id>/{profile,hooks,proofs,templates}.yaml`.

## Adding a segment (copy electrician, 4 files, ~30 min)
1. `mkdir segments/<id>`; copy the 4 yaml files from `segments/electrician/`.
2. `profile.yaml`: pains, offer, close + DM keyword, tone, hashtags.
3. `hooks.yaml`: 8–12 hooks, question/indecision first, buyer named slide 1.
4. `proofs.yaml`: every claim + source + caveat. No invented metrics.
5. `templates.yaml`: copy structures unchanged (they're audience-agnostic).
6. Optional: explicit decks in `slides/generate.py:_SEGMENT_DECKS` for
   `opportunity` + `before_after` (highest-use). Other templates fall back to
   generic copy with the segment close substituted — never leaks another trade's CTA.
7. Test: `generate_slides_deterministic(hook, "<id>", "opportunity")` → close
   contains your DM keyword; beautician decks never mention Tradify, etc.

## Current skins
| Segment | Pains source | Close | Hooks |
|---|---|---|---|
| electrician | playbook (62% missed calls) | DM QUOTE £499 | 16 |
| beautician | SERVICE_CATALOG beauty (no-shows ~£10K/chair) | DM BOOKING £499 | 8 |
| plumber | VISION heating firms (triage, servicing) | DM JOBS £499 | 8 |
| sole_trader | DSIT via VISION (40%/18%, no website) | DM SETUP £499 | 7 |

## What stays shared
State machine, receipt chain, renderer, memory ranking, MCP tools, channels,
house rules (5–8 slides, proof before CTA, one CTA, manual post, leads > views).
