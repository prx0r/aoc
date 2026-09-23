# Peer review response — item-by-item disposition

Review of `6b79405`. Every P0/P1 below is either fixed in tree, tracked in
`docs/`, or explicitly deferred with a reason. Nothing silently dropped.

## P0 — identity collisions (review §2.1)

- **Ad/organic dir collision**: FIXED. Storage path derives from the full
  creative ID (hook+CTA+caption+skin+renderer+offer). Verified live: two CTAs
  → two IDs, two dirs (`test_01_two_ctas_two_ids_no_overwrite`).
- **Paid CTA dropped by DM-inference**: FIXED. `kind=ad` replaces the deck
  close verbatim; verified in final manifest + pixels (`test_02`).
- **ID lacks CTA/slides/caption**: FIXED. All are ID inputs now.
- **Atomic writes**: DONE. Temp sibling + `os.replace`; losers of parallel
  rename races verify-and-share (`test_12_parallel_workers_safe`).
- **Migration map**: DONE. `core/legacy.py` → 72 current, 19 orphaned, 2 missing.

## P0 — evidence gates (review §2.2)

- **Number-overlap matching**: DELETED. `_best_match`/`_matches_known` are
  tombstones that raise. Claims resolve via explicit `claim_refs` or exact
  registry text only (`claims.yaml`, 88 records).
- **62%-of-customers vs 62%-of-calls**: refused, tested (`test_03`).
- **Hook exempt**: hooks pass through `hook-quality-v1` (buyer/number/question)
  and every stat-bearing slide resolves. Non-stat hook lines are offer copy,
  not evidence claims — documented in `core/proof.py`.
- **observed_at**: plans stamp creation time; registry records carry
  `verified_at` (empty = unverified, shown in review). Source freshness is
  NOT yet enforced — tracked: gate needs per-source max-age config.
- **CTA appended post-proof**: FIXED. Final CTA resolves in `render()` from
  the plan, and the proof covers plan slides + close.
- **Historical prices / hypothetical outcomes**: `claims.yaml` types separate
  `first_party_offer` / `third_party` / `hypothetical` (none yet asserted) /
  `measured_outcome` (none yet — zero customers). Caveats render on review.

## P0 — approval enforcement (review §2.3)

- **Sign-off binds asset hash**: DONE. Approval records ZIP + slide hashes;
  any change mints a new ID, so old approvals can't authorize it (tested).
- **Arbitrary content_id approval**: DONE. `sign_off` resolves the build and
  refuses missing/changed creatives; approvals need a human reviewer.
- **Publish without approval**: DONE. `aoc_publish` returns a packet only;
  `aoc_publish_confirm` requires post URL + matching approval receipt +
  drives `approved → ready_for_manual_post → published_confirmed`.
- **BFS invariant**: FIXED. `proof_must_haves_review` now enumerates ALL
  simple paths and requires IN_REVIEW on each.
- **JSONL concurrency**: authoritative lifecycle state moved to SQLite
  (`core/store.py`, transactional sessions); JSONL remains the audit export.

## P0 — analytics feedback loop (review §2.4)

- **Double-counting**: FIXED. UNIQUE(post,observed_at,metric,import_id) +
  `current_totals` from latest observation + interval computation. Tested:
  100→150 yields current 150, interval 50, reimport adds nothing.
- **measure/memory split**: `aoc_measure` still writes receipts (compat);
  `compile_learnings` reads snapshots. Documented as the seam to unify.
- **Placeholder specs**: `compile_learnings` joins content_id where present;
  unattributed snapshots counted apart, never guessed.
- **cpqc honesty**: qualification is an independent event; funnel reports
  leads/qualified/paid/revenue/unattributed separately.

## P0 — review/lookup inconsistency (review §2.5)

- **Full-ID dir lookup**: FIXED. `_resolve_build` scans manifests by
  content_id; short dirs + legacy IDs both resolve.
- **Review re-triggering no-duplicate**: FIXED. Review loads stored gates +
  re-verifies hashes; never re-runs creation gates.

## P1 — contracts (review §2.6)

- **Electrician fallback**: DELETED. Unknown segments raise with known list.
- **business_id adapter**: DONE. CH numbers plus verified booking/profile/
  directory ids; names/handles alone refused. Sole traders representable.
- **Scoring divergence**: documented — aoc scoring is CSV-available fields
  only (max ~55, HOT unreachable); aionboard PROSPECT_SCORING remains the
  commercial authority for call prioritization.

## P1 — docs/outputs (review §2.7)

- README rewritten: JPEGs (not PNGs), executable quickstart, 18→19 MCP
  tools, 11 templates, no phantom CLI modules.
- `store/campaigns.json` remains the committed campaign index; rendered
  ZIPs stay gitignored build artifacts; `core/legacy.py` maps both worlds.

## Deferred (explicit)

- **Source freshness enforcement**: needs per-source max-age config. Tracked.
- **SQLite migration of receipts**: lifecycle state is SQLite; receipt JSONL
  retained as export. Full cutover deferred until concurrent writers exist.
- **CI workflow**: `.github/workflows` not added — no runner access from
  this box to verify. Commands documented in README; `compileall` clean.
- **Static checks/dependency audit**: ruff config absent; stdlib-first core
  kept dependency-free except PIL/yaml/httpx/fastapi boundaries.
