# AUDIT.md — /root/aoc repository audits (appenditive, newest first)

> Rule: never rewrite history. Each audit appends a dated entry.
> Correct prior entries by superseding, not editing.

---

## 2026-09-23 — Beauty shootout: 10 hooks, nails/lashes/hair (94 tests green)

Same rubric. All 10 passed gates first try (loops built in from the
trades lesson). All 10 banked (scores 19-23, all payoff-honest):
- 23 — hair "Out-of-area enquiries waste your week — where's your line?"
  (body: travel-zone economics — exact cash)
- 22 — nails "Stop taking bookings in DMs. It's losing you deposits."
  (body: "DMs don't take deposits. Booking links do." — exact cash)
- 21s — nails deposit trio + hair "Price it once"
- 20s — lashes trio (posting/contrarian, fills/diagnosis, patch/permission)
- 20 — hair "Boosts vs rebooks..." (boost pain already in-bank; template
  didn't surface it this build — segment-grounded, banked with note)

Killed: nails "Your sets deserve better than a messy inbox." (vague
flattery, 11/25). Beauty banks were stronger than remembered (11/11/10
with real specificity) — the gap was formula range (no negatives,
diagnoses, permissions), now filled. Cross-segment pattern emerging:
the best hooks make a check the body cashes on the next swipe.

---

## 2026-09-23 — Copy shootout: 10 hooks, 3 segments (94 tests green)

Rubric (desk, no post data exists): self-ID / specificity / open loop /
payoff honesty / formula freshness, 25 max. Research grounding: negative
framings 1.3-1.8x positive; hook = interrupt + pre-qualify + loop;
dead patterns (founder intro, generic curiosity, aggressive urgency) avoided.

Scoreboard:
- 24 — gardeners "Round workers: how many free cleans did unlogged skips
  give away?" (callout + stakes, body pays off exactly) BANKED
- 21 — gardeners "More customers or fewer skips — which grows your round?" BANKED
- 20 — electrician "Your quotes aren't slow. Your follow-up is. Which do
  you fix first?" (needed a question added; gate rightly rejected v1) BANKED
- 19 — cleaners "Paused plans coming back — without a single phone call?" BANKED
- 19 — gardeners "Still logging rounds on paper?..." (paper pain
  segment-grounded) BANKED
- 18 — cleaners "Cleaning doesn't burn you out. Chasing does — agree?" BANKED
- 17 — electrician "Stop answering every call yourself..." BANKED
- 17 — cleaners "You can stop doing quotes at 9pm. Seriously." BANKED
- 16 — electrician "Quote sent at 2pm, job booked by 4..." REJECTED
  (outcome the body doesn't substantiate — illustrative numbers can't be claims)
- 19raw — electrician "£2,000 CRM vs £20 setup..." REJECTED (£2,000
  unsubstantiated category claim; punch noted, honesty first)

Killed: cleaners pain "never won back — recoverable revenue leaks"
(self-contradicting; rewritten to "Paused plans don't restart themselves —
that revenue leaks every month", verified propagating into new builds).

Lesson: the hook-quality gate's loop requirement (question/number/contrast)
rejected 5/10 first drafts — all bare statements. The gate matches external
research; the drafter (this session) was the weak link, not the gate.

---

## 2026-09-23 — Premium renderer pass (16 segments, 20 tools, 94 tests green)

Scope: `render/slide.py` rewritten from flat-colors to a design system;
patterns sourced from tiktok-carousel-generator, instagram-carousel-mcp,
carousel-english, easy-pil, postcanvas (see commit).

System: Montserrat ExtraBold (vendored `render/fonts/Montserrat-VF.ttf`,
OFL) with shrink-to-fit; accent-anchored gradients + glow + seeded grain;
per-segment deck accents (stable hash); ghost numerals; accent rule;
progress dots; brand wordmark; inverted CTA payoff slides; safe-zone
composition (top 8% / bottom 12% calm).

Rules changed deliberately (not weakened):
- `core/validate.py` backdrop check now accepts bright CTA bands with dark
  text (legibility = contrast, not darkness). CTA wordmark removed instead
  (keeps margins check meaningful on bright slides).
- Old builds keep old bytes (receipts bind asset hashes); new builds get
  the system. content_id has no renderer input, so IDs stay stable.

Verified: 4 fresh decks (electrician/lashes/groomers/plumbers) inspected
at full size + contact sheets; all pixel validation green; renderer
byte-deterministic test added.

---

## 2026-09-23 — Flow verification + hashtag fix (16 segments, 20 tools, 91 tests green)

Scope: wrote `docs/FLOW.md` (every command executed during writing);
fixed all stale counts (19→20 tools, 79→90 tests, 24→26 docs, 13→16 skins,
beautician name); fixed PIPELINE.md legacy refs.

Findings while verifying (both fixed + tested):
- `channel_hashtags` buried segment tags under 8 electrician channel tags
  (`core/channels.py` — segment tags now lead, honoring the module's own
  "segment wins" rule). No silent mis-posting occurred (packets are
  human-read before posting), but a copy-paste poster would have used
  #electrician on nails.
- `load_segment('')` returned an empty skin instead of raising (segments
  root exists, so `.exists()` passed). Now requires a real directory;
  `aoc_publish`'s `except ValueError` guard actually fires.

Tmp verification campaign + build removed from DB/store. Receipts
(gitignored, append-only) retain the trail.

## 2026-09-23 — Full audit (16 segments, 19 tools, 79 tests green)

Scope: every directory, every core module, docs-vs-reality check, upstream
sync check (aionboard OFFER.md, powrobots brand-identity.md).

### Headline numbers (verified live)

| Metric | Value | Verified how |
|---|---|---|
| Segments | 16 | `SEGMENT_IDS` length |
| MCP tools | 19 | `len(TOOLS)` |
| Tests | 79 passing | `pytest tests/ -q` |
| Core modules | 21 files, ~2,500 lines | `wc -l` |
| Docs | 22 files | `ls docs/` |
| Templates | 11 | mcp template list |
| Claims registry | 88+ records | `claims.yaml` |
| Store | 83M, gitignored | `du -sh` |
| Working tree | clean | `git status` |

### LIVE — everything depended upon

- `core/carousel.py` (327) — orchestrator. 9 referrers.
- `core/gates.py` (228) — 9 fail-closed gates. 6 referrers.
- `core/proof.py` (184) — registry resolution, tombstoned fuzzy match. 5 referrers.
- `core/receipt.py` (58) — hash chain. 7 referrers.
- `core/store.py` (212) — SQLite lifecycle + acquisition garden. 6 referrers.
- `core/review.py` (129) — 15-point checklist + bound sign-off. 6 referrers.
- `core/personalize.py` (162) — variants + consent gates. 6 referrers.
- `core/ids.py` (73), `core/schema_manifest.py` (77), `core/fetch.py` (60),
  `core/legacy.py` (76, CLI-only migration tool), `core/memory.py` (82),
  `core/analytics.py` (125), `core/acquisition.py` (137), `core/offers.py` (86),
  `core/validate.py` (74), `core/state.py` (92), `core/backup.py` (168),
  `core/etsy_packet.py` (113), `core/photo_qc.py` (69) — all imported.
- `slides/generate.py` — skins loader, generic decks, hook bank.
- `render/slide.py` — 1080×1920 compositor. `render/etsy.py` — 2400² + MP4.
- `mcp_server.py` — 19 tools, stdio + CLI.
- `web/viewer.py` — gallery + queue on :8798.
- `pi-extension/aoc-sensor.ts` — 6 pi verbs over MCP stdio.
- All 16 `segments/*/`, `claims.yaml`, `offers.yaml`, `channels/*.yaml`.
- `tests/` — 12 files incl. conftest (AOC_DB isolation).

### STALE / DEAD

- `assets/` — EMPTY directory, leftover from early layout. REMOVE.
- `reference/README.md` — describes clones as vendored reference; only the
  README exists locally (clones live in `/root/reference/`, disk-driven
  decision). Accurate but rename pressure: it's a manifest, not a mirror.
- `channels/*.yaml` — present (tiktok/instagram/facebook) but NOT read by
  any code (zero imports). Either wire into plan() or mark advisory-only.
- `store/campaigns.json` — tracked campaign index; references gitignored
  build dirs. Canonical by design (see `core/legacy.py`), but regenerable —
  document that it can be rebuilt via `core/legacy.py::import_legacy`.
- Legacy `store/aoc_<12hex>/` + `store/AOC-XXXXXXXX/` dirs — pre-registry
  builds, resolved via `core/legacy.py`. Never delete (history).

### Upstream sync (verified this audit)

- `offers.yaml` source_commit `65ebc88` CONTAINS live `OFFER.md@266ab4d`
  (ancestor check) — IN SYNC.
- `segments/glimlings/` names (Mosswick, Mab, Puck, Boomoo) match
  `powrobots/docs/brand-identity.md` — IN SYNC.
- powrobots `docs/audit.md:85` zero-import claim for `resolve.py` is STALE
  upstream (it IS imported via MCP) — noted here, NOT our file to fix.

### Prior audits

- (none — this is the first audit entry for /root/aoc)
