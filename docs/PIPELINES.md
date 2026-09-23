# PIPELINES — the seven ways work flows through aoc

Everything runs locally (no network at runtime except R2 backup).
Every pipeline is logged: hash-chained `receipts/*.jsonl` (gitignored,
append-only) + SQLite `store/aoc.db` (gitignored). One identity spine
throughout: `AOC:<64hex>` (see `docs/IDENTITY.md`).

```
idea → BUILD → REVIEW → CAMPAIGN → post (manual) → MEASURE → LEARN
                    ↘ PERSONALIZE (per-business)   ↘ ETSY (listings)
                                                   ↘ BACKUP (R2)
```

## 1. BUILD — idea to gated deck

Entry: `aoc_validate` (cheap, no render) then `aoc_build` / `run_carousel`.

```
hook + template + segment
  → plan()            slides from skin (segments/*/hooks,proofs,templates)
  → proof_from_plan() claims resolve against claims.yaml + segment proofs
  → run_gates()       9 gates, fail-closed (fix the DATA, never the gate)
  → render()          Montserrat system, per-segment accent (render/slide.py)
  → validate_carousel() pixels: dims, contrast, text-present, safe margins
  → export()          tiktok_carousel.zip + contact_sheet.jpg + receipt
```

Output: `store/AOC-XXXXXXXX/` (manifest.json, script.json, slides, ZIP).
Fails anywhere → `carousel_rejected` receipt, nothing rendered. Same hook
rebuilt → no-duplicate gate refuses with the existing receipt id (reuse it).

## 2. PERSONALIZE — per-business variant

Entry: `aoc_personalize` (hook, segment, business, company_number, area).

Consent-gated (`core/personalize.py`): research-only unless a consent record
exists — research variants are stamped do-NOT-send on the receipt. Builds
through the same gated `run_carousel` path, so variant copy must still pass
every gate. Short hooks only (business name counts toward the 12-word cap).

## 3. REVIEW — the human gate

Entry: `python3 -m web.viewer` (:8798) or `aoc_review` + `aoc_signoff`.

Machine first (`core/review.py`: 8 auto checks), then human on the contact
sheet (7 checks, `docs/QUALITY.md`). Sign-off binds the EXACT asset hashes —
any re-render invalidates the approval and needs a new verdict with reason.
`aoc_publish` refuses unapproved revisions; `aoc_publish_confirm` refuses
without a matching approval. Nothing posts itself, ever.

## 4. CAMPAIGN — track start to finish

Entry: `aoc_campaign` (create; pass `content_id` to link the first
creative) + `link_creative` (python API, `core.acquisition`) per extra creative.

```
campaign → link approved creatives (CRT: ids)
  → aoc_publish        packet: ZIP + sheet + caption + CTA + hashtags + checklist
  → MANUAL POST        TikTok Photo Mode + trending sound (no tool exists on purpose)
  → aoc_publish_confirm needs the REAL post URL (empty/refused otherwise)
  → aoc_metrics        snapshot views/saves/leads against post_id + content_id
  → record_lead / qualification / conversion (separate events, joined by campaign)
  → aoc_funnel         leads → qualified → paid → revenue (never guessed)
```

Enquiry ≠ qualified; unattributed revenue reported apart. Funnel zeros
before posting is correct, not broken.

## 5. LEARN — close the loop

Entry: `aoc_rank` (sort by leads/sales, never views) + `aoc_learn`.

Observations land in namespaced memory (`aionboard` vs `powthings` vs
`garden` — never mixed). Two writers, one store: `aoc_metrics` (post
snapshots keyed by URL) and `aoc_measure` (direct content_id observations);
both feed `core/memory.py`. Learnings mutate the next batch: same angle,
new hook wording; kill losers. Hook banks (`segments/*/hooks.yaml`) are the
standing army — every line must pass gates (bank-hygiene test enforces it).

## 6. ETSY — listing packets (manual end-to-end)

Entry: `core/etsy_packet.build_packet` via python (no MCP tool yet — gap).

Validates listing copy, emits photo slots (WHAT to shoot — real photography
still required) + type slots (renderable cards) + video slot. Nothing
uploads; Etsy Shop OAuth doesn't exist here. See `docs/ETSY.md`.

## 7. BACKUP — R2 (the only network call)

Entry: `aoc_backup`. Uploads ZIP + manifest to the `aoc-assets` bucket,
verifies after write, logs a `backed_up` receipt. Creds from `.env`
(gitignored; `.env.example` is the template). Everything else works offline.

## State map

| lives in | what | survives |
|---|---|---|
| `store/AOC-XXXXXXXX/` | slides, ZIP, manifest, script | prunable build output (receipts outlive it) |
| `receipts/*.jsonl` | hash-chained event log | append-only, never edited |
| `store/aoc.db` | content_state, campaigns, leads, funnel | gitignored; tmp DBs in tests |
| `store/campaigns.json` | campaign index | gitignored |
| git | code, skins, claims, offers, docs, tests | the only thing pushed |
