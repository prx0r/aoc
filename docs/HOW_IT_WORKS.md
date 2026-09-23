# HOW_IT_WORKS — the complete notes on aoc

> Read this first. Everything else is detail.

## What aoc is

TikTok slideshow factory for AI Onboard's 13 UK trade segments. Deterministic
pipeline: hook → gated slides → 1080×1920 JPEGs → ZIP → human review →
manual TikTok post → measured learnings. No auto-posting, ever.

## The pipeline (one command per stage)

```
plan()              hook + template + segment → script JSON (claim_refs attached)
  ↓
proof_from_plan()   every stat claim resolves to claims.yaml or REFUSED
  ↓
run_gates()         9 gates; failure → FAIL receipt + raise, nothing renders
  ↓
render()            slides → PNGs, atomic rename; replay detection on duplicates
  ↓
validate_carousel() pixel checks (dims, backdrop, text, margins) + contact sheet
  ↓
run_review()        8 automated checklist items; 7 queued for human
  ↓
export()            hash-verified ZIP
  ↓
sign_off()          human verdict bound to exact asset hashes
  ↓
publish packet → manual post → publish_confirm → measure → learn
```

Run it: `run_carousel(hook, template, segment=...)` in `core/carousel.py`.
Cheap check first: `aoc_validate` (proof+gates, no render).

## Identity model (4 IDs, never confused)

| ID | Covers | Example |
|---|---|---|
| `experiment_id` | segment + offer + template + channel (stable test) | `EXP:abc…` |
| `content_id` | hook + CTA + caption + skin + renderer + offer version (immutable revision) | `AOC:abc…` |
| `asset_id` | content_id + ZIP sha (what was actually approved) | `AOC:…:sha256:…` |
| `post_id` | platform + account + platform post ID (only on confirm) | `tiktok/@x/123` |

Filesystem uses short display form (`AOC-XXXXXXXX`); full hash is identity.
Same hook + different CTA = different IDs, different dirs. Renderer changes
bump `RENDER_V` so old pixels never collide with new.

## Gates (9, fail-closed)

`evidence-fresh` (claims resolve) · `no-duplicate` (same creative exists) ·
`claim-resolved` (every slide traces) · `hook-quality` (buyer/number/question,
≤12 words) · `render-legible` (4–8 slides, word limits, no dupes) ·
`personalization` (identity + consent evidence) · `offer-fresh` (registry
version current) · `offer-cta` (close carries current price) ·
`suppression` (withdrawn permission blocks everything).

## Skins (engine never names a trade)

`segments/<id>/{profile,hooks,proofs,templates,manifest}.yaml` + `PAINS.md` +
`CAMPAIGN.md`. 13 segments. Deck resolution: explicit hand-tuned →
generic skin-driven → refuse (never another trade's copy).
New segment = copy electrician's 4 YAMLs, ~30 min (`docs/SEGMENTS.md`).

## Claims & offers (the anti-hallucination layer)

- `claims.yaml` (88 records): every public fact with type
  (first_party_offer / third_party / hypothetical / measured_outcome),
  source, permitted segments, status. Number-overlap matching is DELETED;
  unknown stats raise, pending ones queue for review.
- `offers.yaml`: versioned £20 quickstart (waitlist) + £499 standard,
  snapped from aionboard OFFER.md with commit pinned. A registry bump
  invalidates pending creatives; history replays against its version.

## Review (15-point checklist, 8 auto + 7 human)

Auto: hook-names-viewer, no-dupes, contrast, safe-zones, claims-sourced,
no-invented-numbers, single-CTA, trackable. Human (contact sheet):
hook-match, arc, 2-second read, continuity, caption, disclosure, recorded
verdict. `sign_off` binds ZIP+slide hashes — re-rendered pixels invalidate
old approvals. `docs/QUALITY.md`.

## Analytics (append-only truth)

`snapshots` append, never overwrite. Current totals = latest observation;
intervals derive from consecutive pairs; reimports dedupe on
(post, time, metric, import_id). Save-rate is the completion proxy.
Rank by leads → sales, never views. Zero posts measured yet — loop armed.
`docs/ANALYTICS.md`.

## Acquisition chain (SQLite `store/aoc.db`)

campaigns → creatives → posts → observations → leads →
qualifications → conversions (+ experiments, suppression, events log).
Enquiry ≠ qualified conversation (independent event). Unattributed
conversions reported apart, never guessed. Contact details never leave the DB.

## Interfaces

- **MCP (20 tools)**: status/hooks/build/validate/inspect/lineage/measure/
  publish(+confirm)/rank/receipts/backup/review/signoff/metrics/learn/
  score/personalize/funnel/campaign. stdio + `mcp_server.py <tool> '<json>'` CLI.
- **Viewer** (`python3 -m web.viewer`, :8798, localhost): gallery, queue,
  per-creative view, sign-off forms, ZIP downloads, `/api/status`.
- **Pi extension** (`pi-extension/aoc-sensor.ts`): 6 verbs over MCP stdio.
- **Backup** (`core/backup.py`): R2 uploads, verify-after-write, receipts.
  Creds from env/`.env` only — never in repo.

## File map

| Path | Role |
|---|---|
| `core/carousel.py` | orchestrator (plan→proof→gates→render→validate→export) |
| `core/{gates,proof,ids}.py` | 9 gates, claims resolution, canonical IDs |
| `core/{state,store}.py` | in-memory lifecycle + SQLite persistence |
| `core/{review,validate}.py` | 15-point checklist, pixel checks, contact sheets |
| `core/{memory,analytics,acquisition}.py` | rankings, snapshots→learnings, funnel |
| `core/{personalize,offers}.py` | per-business variants, offer registry |
| `core/{receipt,fetch,schema_manifest,legacy}.py` | hash chain, fetch envelope, schemas, ID migration |
| `core/backup.py` | R2 uploads |
| `slides/generate.py` | skins loader, generic decks, hook bank |
| `render/slide.py` | PIL 1080×1920 compositor |
| `mcp_server.py` | 20 tools, stdio + CLI |
| `web/viewer.py` | local gallery + queue |
| `segments/*/` | 16 skins + strategies |
| `claims.yaml` / `offers.yaml` | registries |
| `store/` | builds (gitignored) + `campaigns.json` index + `aoc.db` |
| `receipts/` | hash-chained logs (gitignored) |
| `tests/` | 75 tests incl. 12 peer-review regressions + 3 E2E scenarios |

## Invariants (break these and the tests fail)

1. No render without passing gates. 2. No approval without exact asset hashes.
3. No publish without approval + real post URL. 4. No invented numbers.
5. Unknown segments raise. 6. Withdrawn permission blocks everything.
7. Snapshots append, never overwrite. 8. Leads ≠ qualified. 9. Views ≠ value.
