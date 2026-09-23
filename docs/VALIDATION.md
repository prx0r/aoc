# VALIDATION — how we know a slideshow is actually good

Honest split: machines check structure + pixels, humans check taste.
Automated gates catch bad work before render. Contact sheets make review fast.

## What machines check (fail-closed, pre-render)

`core/gates.py` — ported from `/content/core/gates.py`, plus two render gates:

| Gate | What | Fail example |
|---|---|---|
| evidence-fresh-v1 | every stat claim traces to `proofs.yaml` id | "saved clients 99% overnight" → refused |
| no-duplicate-v1 | same hook+template has no ok receipt | rebuild of a built deck → refused |
| claim-resolved-v1 | every slide traces to hook/proof/close | empty slide, orphan stat |
| hook-quality-v1 | hook ≤12 words, names buyer or number, asks/compares | "AI can transform your business today" → refused |
| render-legible-v1 | 4–8 slides, hook ≤12 words, body ≤18, no dup text | 3-slide deck, 25-word slide |

`core/proof.py` — plan becomes a frozen Proof (claims + evidence_refs + observed_at).
Untraced stats raise before anything renders. Near-matches count (same figure,
different wording → same proof id recorded).

## What machines check (post-render, pre-export)

`core/validate.py` — opens the actual PNGs:
- dims exactly 1080×1920, valid JPEG
- dark text band present (band luminance < 150)
- text actually drawn (luminance spread > 40)
- top 8% / bottom 12% calmer than band (clear of TikTok UI zones)

## What humans check (contact sheet)

Every build writes `contact_sheet.jpg` — all slides in one grid (ai-ugc pattern).
Review takes 10 seconds: buyer named slide 1? one idea per slide? proof before CTA?
`draft → in_review → approved|rejected` in `core/state.py`; rejection needs a reason.

## MCP surface (mirrors /content)

`python3 mcp_server.py <tool> '<json>'` or stdio. 10 tools:
`aoc_status/hooks/build/validate/inspect/lineage/measure/publish/manual-pending/rank/receipts`.
- `aoc_validate` — proof+gates WITHOUT rendering. Cheap: run before every build.
- `aoc_publish` — always returns manual-pending. No auto-post by design
  (matches the Reddit lesson: drafts + approval beats full automation for trust).
- `aoc_measure` — metrics into receipt chain + memory (leads/sales, never views alone).

## What we deliberately do NOT automate
Taste, humor, timing, trending-audio choice, and whether a claim *feels* true.
Gates enforce structure; the contact sheet + human gate enforce judgment.
