# THREADS.md — open threads for /root/aoc

> What can be picked up next, and what's blocking it. Updated 2026-09-23.
> Closed threads move to the log at the bottom, never deleted.

## Open

### T1 — First real TikTok post + measurement
**Status:** open. **Blocks:** the entire learning loop (armed, unfired).
**What:** post one approved carousel manually, record metrics via `aoc_metrics`,
run `aoc_learn`, mutate. Until this happens every ranking is untested.
**Effort:** 1 day (account exists assumed).

### T2 — Real product photography
**Status:** open. `core/photo_qc.py` waits for camera photos; typography cards
stand in. Etsy slot 1 must become real photography when it exists.
**Effort:** ongoing (shoot) + 0 code.

### T3 — Etsy API draft integration
**Status:** spec'd (`docs/ETSY.md` §5), not built. Needs Etsy app + OAuth click
(human step), then `createDraftListing` → uploads. Drafts only, never auto-publish.
**Effort:** 2–3 days after OAuth.

### T4 — Channels wiring decision
**Status:** CLOSED. Wired: `plan()`/`run_carousel()` refuse unknown channels,
`aoc_publish` packet carries channel hashtags (merged with segment tags) +
channel checklist. Segment wins on conflict.
(`core/channels.py`, `TestChannels`.)

### T5 — Video beyond Etsy MP4s
**Status:** `render/etsy.py:render_video` covers silent slideshows. TikTok-native
video (voiceover, motion) explicitly out of scope until a strategy demands it.

### T6 — powthings offer
**Status:** blocked on the business, not the code. `powthings-preview` is
unavailable/launch-list until prices validate. No code action.

### T7 — Garden-familiars Etsy launch
**Status:** copy + packets ready (4 listings pass all rules), no shop exists.
Blocked on product photography + Etsy shop creation (human steps).

### T8 — Source freshness enforcement
**Status:** deferred (see `docs/PEER_REVIEW_RESPONSE.md`). Needs per-source
max-age config in claims registry.

## Open — identity hardening (from 2026-09-23 e2e run)

- T-prefix: tooling must never match builds by hook prefix (caused a
  mis-signed approval; caught by hash check). Grep for `startswith` on
  hooks in any new tooling. Status: fixed in `mcp_server` paths used.
- T-fictional: demo posts flip real `content_state`; revert to `in_review`
  after. Consider a `--demo` flag that redirects receipts+DB to tmp.

## Closed log

- 2026-09-23: Bank hygiene crisis (49 failing hooks) → recalibrated gates,
  rewrote weak hooks, locked with test (`test_all_bank_hooks_pass_gates`).
- 2026-09-23: Proof↔pain restatements collapsing decks (6 skins) → angled
  proofs + overlap dedupe + matrix test.
- 2026-09-23: Receipt-chain-affecting sign-off on wrong ID → public
  `review_corrected` receipt; rule: resolve IDs from manifests, never memory.
