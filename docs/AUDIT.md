# AUDIT.md — /root/aoc repository audits (appenditive, newest first)

> Rule: never rewrite history. Each audit appends a dated entry.
> Correct prior entries by superseding, not editing.

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
