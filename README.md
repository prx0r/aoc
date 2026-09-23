# aoc — AI Onboard Content

TikTok slideshow factory for AI Onboard (+ POW Things companions).
Generates 9:16 image carousels for 16 segments: electrician, beautician, nails,
lashes, hair, cleaners, dog_groomers, gardeners, car_detailers,
driving_instructors, weddings, plumber, sole_trader, powthings,
garden_familiars, glimlings.

**Path:** £0 organic TikTok → £70 Facebook test → £30 reserve

## Pipeline

```
OFFER/HOOK → SLIDE COPY → RENDER JPEGs → ZIP → HUMAN APPROVE → TIKTOK POST
```

## Quick Start (executable on a clean checkout)

```bash
pip install pillow pyyaml httpx pytest
python3 -m pytest tests/ -q -m "not slow"  # unit suite, no network

# Build one carousel (gated, receipted)
python3 -c "
from core.carousel import run_carousel
r = run_carousel('UK electricians — still doing quotes at 9pm?', 'opportunity', segment='electrician')
print(r['zip'])"

# Validate without rendering
python3 mcp_server.py aoc_validate '{"hook": "UK electricians — still doing quotes at 9pm?", "segment": "electrician"}'

# Review queue in browser
python3 -m web.viewer  # http://127.0.0.1:8798/
```

Config: `AOC_DB` (SQLite path, default `store/aoc.db`), `R2_*` (backup creds,
via `.env`, never committed). No hidden dependency on `/root/aionboard` —
the offer registry (`offers.yaml`) and claims (`claims.yaml`) are snapshotted
in-repo with upstream revisions recorded.

## Templates (11)

`opportunity` · `before_after` · `faq` · `social_proof` · `demo` ·
`diagnostic` · `teardown` · `comparison` · `annuity` · `retention` ·
`waitlist` (UK Muse waiting list) · `trust` (TRUST_MODEL guarantees).
See `docs/TEMPLATES.md` for structures and `segments/*/templates.yaml`.

## Hook Bank (Tested Patterns)

From research: question/indecision hooks outperform declarative product hooks.

```
"Electricians: which of these would you automate first?"
"UK electricians — still doing quotes at 9pm?"
"Landlords need EICRs every 5 years. Who owns that cycle?"
"Marketplace takes 20% of your new clients. Whose business is it?"
"Just downloaded Muse? We'll set it up for your business for £20."
```
Per-segment banks live in `segments/*/hooks.yaml` (all gate-passing; enforced by test).

## Creative Memory

Tracks performance: `audience × hook × angle × slide_count × CTA × visual_style → views, swipes, profile_visits, clicks, leads, sales`

Prefers mutations of patterns that produced qualified leads, not just views.

## Docs (29 files)

Start: `docs/HOW_IT_WORKS.md` → `docs/AUDIT.md` (latest state) → `THREADS.md`
(open work). Then by need: `AGENT_CONTROL` (full API/CLI reference for
driving every layer), `PIPELINES` (map of all 7 pipelines),
`FLOW` (full campaign flow, every command executable), `PIPELINE` (the £100
experiment plan), `IDENTITY` (how one creative stays itself), `VALIDATION` + `QUALITY`
(review it), `TEMPLATES` + `SEGMENTS` + `VERTICALS` (extend it),
`LEARNING_LOOP` (measure it), `ETSY` + `MONETIZATION` (sell it),
`PLATFORM` (federate it), `PEER_REVIEW_RESPONSE.md` (why it's shaped so).

20 MCP tools (`aoc_status/hooks/build/validate/inspect/lineage/measure/publish(_confirm)/rank/receipts/backup/review/signoff/metrics/learn/score/personalize/funnel/campaign`).
See `docs/VIEWING.md` for the local gallery + pi extension.

## Directory Structure

```
aoc/
├── core/              # State machine, gates, receipt chain
├── render/            # PIL-based 1080x1920 slide renderer
├── slides/            # Slide copy generation (LLM or deterministic)
├── channels/          # TikTok, Instagram, Facebook profiles
├── receipts/          # Hash-chained content log
├── store/             # Rendered slides, scripts, ZIPs
├── segments/          # 16 skins (engine never names a trade)
│   ├── electrician/   # ↔ aionboard electrician (10k prospects)
│   ├── beautician/    # ↔ beauty (+nails/lashes/hair)
│   ├── nails/ lashes/ hair/          # beauty sub-niches, own prices
│   ├── cleaners/ dog_groomers/ gardeners/
│   ├── car_detailers/ driving_instructors/ weddings/
│   ├── plumber/       # aoc-original (no aionboard pack yet)
│   ├── sole_trader/   # aoc-original (general gap)
│   ├── powthings/ garden_familiars/ glimlings/  # POW companion lines
│   └── each: profile,hooks,proofs,templates,manifest.yaml + PAINS/CAMPAIGN.md
├── reference/         # Manifest of external clones (see reference/README.md)
├── docs/              # 29 docs — start with HOW_IT_WORKS.md, then AUDIT.md
├── THREADS.md         # Open work
└── tests/             # Pipeline tests (90 green)
```

## What We Stole

| From | Pattern | Why |
|------|---------|-----|
| ClipFactory | PIL slide renderer | 40-line production-tested renderer |
| content-management-dashboard | State machine + approval | Structural human-in-the-loop guarantee |
| ai-ugc-slideshows | Research → content → publish | JSON-as-contract pipeline |
| clawvisual | MCP-compatible tools | Agent-driven generation |
| /content | Receipt chain + gates | Provenance and dedup |
