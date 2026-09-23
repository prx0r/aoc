# aoc — AI Onboard Content

TikTok slideshow factory for AI Onboard. Generates 9:16 image carousels for UK electricians.

**Path:** £0 organic TikTok → £70 Facebook test → £30 reserve

## Pipeline

```
OFFER/HOOK → SLIDE COPY → RENDER PNGs → ZIP → HUMAN APPROVE → TIKTOK POST
```

## Quick Start

```bash
# Generate a slideshow from a hook
python3 -m slides.generate --hook "UK electricians — still doing quotes at 9pm?" --template opportunity

# Render slides as 1080x1920 PNGs
python3 -m render.slideshow --input store/latest/script.json

# Export ZIP for TikTok upload
python3 -m render.export --input store/latest/

# Review in browser
python3 -m core.review
```

## Templates

| Template | Scenes | Use For |
|----------|--------|---------|
| `opportunity` | hook → proof → workflow → close | "AI can do X for your business" |
| `before_after` | hook → before → after → close | "Before vs after AI setup" |
| `faq` | hook → question → answer → close | Common electrician questions |
| `social_proof` | hook → stat → testimonial → close | "40% of sole traders use AI" |
| `demo` | hook → screen_recording → result → close | Actual workflow demonstration |

## Hook Bank (Tested Patterns)

From research: question/indecision hooks outperform declarative product hooks.

```
"Which of these would you automate first?"
"Am I doing this wrong?"
"What would you automate first?"
"UK electricians — still doing quotes at 9pm?"
"Your competitors are using AI. Are you?"
"The quote you sent at 11pm — AI could've sent it at 2pm"
```

## Creative Memory

Tracks performance: `audience × hook × angle × slide_count × CTA × visual_style → views, swipes, profile_visits, clicks, leads, sales`

Prefers mutations of patterns that produced qualified leads, not just views.

## Docs

- `docs/HYPOTHESIS.md` — the bet, the £100 split, what counts as winning
- `docs/MINING.md` — what we stole from each reference repo
- `docs/PIPELINE.md` — how to run the experiment end-to-end
- `reference/README.md` — where the clones live (not vendored)

Proven: `store/aoc_66b19fb4c46b/` — 7 slides + ZIP from one command. MCP: 5 tools (`aoc_status/hooks/build/rank/receipts`).

## Directory Structure

```
aoc/
├── core/              # State machine, gates, receipt chain
├── render/            # PIL-based 1080x1920 slide renderer
├── slides/            # Slide copy generation (LLM or deterministic)
├── channels/          # TikTok, Instagram, Facebook profiles
├── receipts/          # Hash-chained content log
├── store/             # Rendered slides, scripts, ZIPs
├── assets/            # Images, hooks, proofs, templates
│   └── electrician/   # Electrician-specific content
├── reference/         # Cloned reference repos
├── docs/              # Architecture, protocols
└── tests/             # Pipeline tests
```

## What We Stole

| From | Pattern | Why |
|------|---------|-----|
| ClipFactory | PIL slide renderer | 40-line production-tested renderer |
| content-management-dashboard | State machine + approval | Structural human-in-the-loop guarantee |
| ai-ugc-slideshows | Research → content → publish | JSON-as-contract pipeline |
| clawvisual | MCP-compatible tools | Agent-driven generation |
| /content | Receipt chain + gates | Provenance and dedup |
