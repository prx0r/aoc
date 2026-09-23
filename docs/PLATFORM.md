# PLATFORM — aoc as the general content platform

> Status: SPEC (not yet built). Phase 1 is the only authorized work.

## 0. One-paragraph version

`aoc` owns the pipeline (plan → proof → gates → render → validate → review
→ publish → measure → learn). Data gardens plug in as signal adapters.
Renderers plug in as output formats (photo live, video stubbed). Segments
stay audiences; gardens stay evidence. Every combination is gated, receipted,
and reviewable through one queue, one MCP surface, one viewer.

## 1. Non-goals (load-bearing)

1. No repo merger with `/content`. Federation via contracts, not shared code.
2. No auto-posting, ever. No uploader tools, no scheduler that publishes.
3. No new segments/templates until Phase 1 proves the garden→slide thread.
4. No invented metrics: adapters report `SUCCESS_EMPTY` on missing data.

## 2. Target directory layout

```
aoc/
├── core/                 # UNCHANGED kernel (ids, gates, proof, receipt,
│                         # state, store, review, validate, memory,
│                         # analytics, acquisition, offers, personalize,
│                         # fetch, backup, schema_manifest, legacy)
├── gardens/              # NEW: signal adapters, one file per garden
│   ├── __init__.py       #   registry: garden_id → adapter + capability probe
│   ├── base.py           #   Signal dataclass + FetchResult envelope
│   ├── powpowpow.py      #   anomaly/ranking/concept/thesis (needs JSONL)
│   ├── ukgraph.py        #   geo_signal/ranking (needs JSONL) ← PHASE 1
│   ├── ukproducts.py     #   flip margins (stub until data present)
│   ├── ashe.py           #   wage change (stub)
│   ├── hpi.py            #   type divergence (stub)
│   └── boring.py         #   delay penalties (stub)
├── render/
│   ├── slide.py          # photo carousel (LIVE)
│   └── video.py          # NEW STUB: HyperFrames adapter, raises NotWired
│                         # until garden data + renderer exist on this box
├── slides/
│   ├── generate.py       # + from_signal(signal, segment, template)
├── segments/             # audiences (13, unchanged shape)
├── channels/             # tiktok/facebook/instagram (+ youtube on video live)
├── claims.yaml           # + garden-sourced claims (namespaced garden.*)
├── offers.yaml           # unchanged
├── mcp_server.py         # + garden_* tools (read-only signal queries)
├── web/viewer.py         # + media-type tabs (carousels | videos)
├── pi-extension/         # + garden query verb
└── docs/PLATFORM.md      # this file
```

## 3. Contracts

### 3.1 Signal (gardens → engine)

```yaml
signal_id: "ukgraph:planning:2026-09-23:extensions-49"  # garden:kind:date:slug
garden: ukgraph
kind: geo_signal | ranking | comparison | anomaly | concept | thesis
title: "49 planning apps hint near-term electrical work"
claim: "49 of 100 recent applications mention extensions or conversions"
metrics: [{name: matching_applications, value: 49, unit: count}, ...]
evidence: [{file: <path>, observed_at: <iso>}]   # ≥1 required, else refused
entities: [electrician, extension, conversion]
updated_at: <iso>
```

Adapter health: `probe() → {ok, rows, latest_observed_at, missing: [...]}`.
Missing data → `FetchResult(FAILED)`; empty-but-healthy → `SUCCESS_EMPTY`.
Adapters NEVER synthesize rows.

### 3.2 Plan extension (engine accepts signals)

`plan()` gains optional `signal: dict`. When present:
- `plan["signal_id"]`, `plan["garden"]` recorded; `experiment_id` includes
  `signal_id` + `garden` (new experiment family, no ID collision).
- `proof_from_plan` resolves signal metrics as evidence (same claim rules:
  exact registry text or explicit ref; no fuzz).
- `slides/generate.from_signal(signal, segment, template)` maps
  signal.kind → template default (anomaly→opportunity, ranking→opportunity,
  comparison→vs, geo_signal→map/opportunity) with hook drafted from
  signal.title, then normal gates apply unchanged.

### 3.3 Cross-repo lineage

Receipts stay per-repo. Cross-references by ID only:
`{repo: "content", kind: "video", id: "vid_…"} ↔ {repo: "aoc", kind: "carousel"}`.
`aoc_lineage` resolves local side; remote side is a pointer, never copied.

### 3.4 Renderer contract

```python
render_artifact(plan: dict, out_dir: Path) -> Manifest
# Manifest: {content_id, slides|scenes, sha256:{}, duration_s?, format: "photo"|"video"}
```

Both renderers satisfy it. `render.slide` does today. `render.video`
raises `NotWiredError("needs <paths>")` listing exactly what's missing.
Gates/validate/review/measure learn nothing new — they consume Manifests.

## 4. Pipelines (all five, end to end)

### P1. Segment carousel (LIVE — unchanged)
hook → slides → PNGs → ZIP → review → manual post → measure → learn.

### P2. Signal carousel (PHASE 1)
garden JSONL → adapter signal → `from_signal` → gates → PNGs → ZIP →
review → manual post → measure → learn. First proof: ukgraph planning →
electrician opportunity. If the JSONL is absent, the adapter says so and
the run stops with a `no-data` receipt (not an empty carousel).

### P3. Per-business variant (LIVE — unchanged)
CSV row → scored → identity-token variant → gates incl. consent →
receipt stamped research-only/consented.

### P4. Paid ad (LIVE — unchanged)
like P1/P2 with `kind=ad`, explicit qualifying CTA, separate IDs.

### P5. Video (STUBBED — explicitly not built)
signal → proof → gates → `render.video` → FAIL receipt `not-wired`
until data + HyperFrames land. The stub exists so callers fail loudly
with a shopping list instead of silently producing nothing.

## 5. Segment × garden matrix (what combinations are real)

| Segment \ Garden | offer-led (today) | ukgraph | powpowpow | others |
|---|---|---|---|---|
| electrician | ✅ live | P1 target | future | stub |
| nails/lashes/hair | ✅ live | future (salon planning?) | — | stub |
| cleaners/plumber/sole_trader | ✅ live | future | — | stub |
| +9 niche skins | ✅ live | future | — | stub |

Rule: a cell opens only with (a) adapter data present, (b) one proven
carousel, (c) human sign-off. No speculative matrix-filling.

## 6. MCP surface (additive only)

Existing 19 tools unchanged. New read-only tools:
- `garden_status` — per-garden probe (rows, freshness, missing paths)
- `garden_signals garden limit` — top signals with evidence
- `aoc_build --signal` — plan accepts `signal_id` (resolved server-side;
  raw signal JSON accepted too and hashed into the plan)

No publish/uploader/scheduler tools. Ever.

## 7. Viewer (additive)

Media tabs: `carousels | videos | all`. Video tab renders empty state
("no video renderer on this box — see render/video.py") until P5 unblocks.
Queue/review/sign-off shared across media. `/api/status` gains
`gardens: {id: {ok, rows, latest}}`.

## 8. Pi extension (one new verb)

`aoc_garden_signals(garden)` → top signals. Existing 6 verbs unchanged.
Shape identical to content-sensor.ts (spawn-stdio, tools/call, timeout).

## 9. Testing (extends current 75)

- Adapter contract tests: missing dir → FAILED (not empty); empty dir →
  SUCCESS_EMPTY; malformed row skipped + counted, never half-parsed.
- `from_signal` tests: evidence-less signal refused; metric-less refused;
  hook drafted from title; gates apply unchanged.
- Video stub test: raises NotWiredError naming missing paths.
- Matrix test: only allowlisted (segment, garden) pairs build.
- E2E P2 scenario (fictional ukgraph JSONL in tmp): signal → carousel →
  receipt chain verifies, manifest carries garden + signal_id.

## 10. Migration from current state (ordered, each shippable)

1. `gardens/base.py` + registry + `garden_status` tool (no data needed).
2. `gardens/ukgraph.py` adapter (reads JSONL if present, else FAILED).
3. `from_signal` + experiment_id garden family + 1 proven carousel.
4. `render/video.py` stub + viewer video tab + matrix doc row.
5. Remaining adapters as data appears. Never stub data — stub renderers only.

## 11. Acceptance for Phase 1 (all must hold)

- [ ] `garden_status` reports ukgraph missing-data honestly on this box
- [ ] Fictional ukgraph JSONL in tmp → full P2 run → gated ZIP + receipts
- [ ] Real-data absence produces `no-data` receipt, never an empty carousel
- [ ] No existing test broken; new adapter tests green
- [ ] Docs updated (`docs/PLATFORM.md` status line flipped to Phase-1-done)

## 12. Open questions (decide with data, not now)

- Should R2 backup cover garden JSONL snapshots? (Probably yes, later.)
- Shared contact/audience taxonomy between segments and garden entities?
- Does powstock feed a garden adapter? (Out of scope: different repo, different owner.)
