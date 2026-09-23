# AGENTS.md — aoc

TikTok slideshow factory for AI Onboard (+ POW companion lines). Deterministic
pipeline, fail-closed gates, human review, measured learning loop. 16 segments ·
20 MCP tools · 94 tests green · 27 docs. State: `docs/AUDIT.md` (newest first),
open work: `THREADS.md`, pipeline map: `docs/PIPELINES.md`.

## How it all works

**Idea → deck.** `run_carousel(hook, template, segment)` (or `aoc_build`) runs
plan → proof → gates → render → pixel-validate → export. Plan pulls copy from
the segment skin (`segments/<id>/`: profile, hooks, proofs, templates +
PAINS/CAMPAIGN.md). Proofs resolve every claim against `claims.yaml` + segment
proofs — unknown stats raise, never invent. Render is the Montserrat system
(`render/slide.py`, per-segment accent, ghost numerals, inverted CTA slide,
safe-zone composition). Output lands in `store/AOC-XXXXXXXX/` with manifest +
script + ZIP + contact sheet; a `carousel_built` receipt binds asset hashes.

**Identity.** One `AOC:<64hex>` from plan → manifest → receipt → approval →
publish → observations. Same copy = same ID (renderer isn't an ID input);
any re-render needs a new approval. Resolve IDs from manifests on disk —
never from memory, never by hook prefix (two builds once shared a prefix and
nearly got cross-signed; the hash check caught it).

**Gates (9, fail-closed).** Hook must name the buyer/number AND open a loop
(question/number/contrast — bare statements are rejected, correctly).
Render-legible caps slide length; evidence-fresh + claim-resolved enforce
sourcing; offer gates pin copy to `offers.yaml` versions; suppression blocks
unconsented personalization. If a build refuses, fix the DATA (skin/hook),
not the gate. Weakening a gate needs a written reason in the commit.

**Review.** Machine (`core/review.py`, 8 auto checks) then human on the
contact sheet (`python3 -m web.viewer`, :8798). `aoc_signoff` needs decision +
reason + reviewer; approval binds exact hashes. `aoc_publish` emits a packet
(ZIP + caption + CTA + hashtags + checklist) — manual-pending, never posted.
`aoc_publish_confirm` needs the REAL post URL. No auto-post tool exists and
none may be built.

**Campaigns.** `aoc_campaign` (+ `link_creative` for extras) → publish packet
→ manual TikTok post → confirm → `aoc_metrics` → lead/qualification/conversion
events → `aoc_funnel`. Enquiry ≠ qualified; unattributed revenue stays apart;
funnel zeros before posting is correct. Learning via `aoc_rank`/`aoc_learn`
(rank by leads, never views), namespaces isolate lines (`aionboard`,
`powthings`, `garden`).

**Variants + side pipelines.** `aoc_personalize` builds per-business variants
(consent-gated, research-only default; business name counts toward word caps).
Etsy packets via `core/etsy_packet.build_packet` (python API only, manual
photography/upload — no MCP tool yet). `aoc_backup` pushes to R2 (only network
call; creds in `.env`, never committed).

**Logging.** `receipts/*.jsonl` hash-chained + append-only (never edit);
`store/aoc.db` holds content_state/campaigns/leads (gitignored); `store/` is
prunable build output (receipts outlive it — tests skip pruned builds).
Git holds code, skins, claims, offers, docs, tests — nothing else.
Legacy `aoc_<12hex>` IDs map via `python3 -m core.legacy store` (read-only).

## Commands

- `python3 -m pytest tests/ -q` — full suite (94, no network)
- `python3 mcp_server.py aoc_validate '{"hook":"...","segment":"nails"}'` — cheap gate check
- `python3 mcp_server.py aoc_build '{"hook":"...","template":"opportunity","segment":"nails"}'` — build
- `python3 -m web.viewer` — gallery + review queue (:8798)
- Tests self-isolate: conftest points `AOC_DB` at a tmp dir per test
  (`core/store.py` honors `AOC_DB`; receipts go to tmp paths too)

## Do not

- Add segments/templates without updating `SEGMENT_IDS` dependents
  (`docs/SEGMENTS.md`, `docs/VERTICALS.md`, MCP template lists).
- Quote prices anywhere except via the offer registry + segment close.
- Invent stats, URLs, or post outcomes. Fictional demos stay out of the real
  DB (revert content_state; receipts stay, labeled).
- Match builds by hook prefix. Match by full content_id from manifests.
- Weaken gates, edit receipts, force-push history, or commit secrets/ZIPs/JPGs/DBs.
