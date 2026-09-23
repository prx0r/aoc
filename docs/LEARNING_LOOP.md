# LEARNING_LOOP — how runs are organized, tracked, and reused

## Where a run lives

One build = one directory + receipts + DB rows, all keyed by content_id:

```
store/AOC-XXXXXXXX/          # short display dir (full AOC:<64hex> in manifest)
  script.json                # plan: hook, slides, CTA, claim_refs, offer version
  slide_*.jpg                # rendered slides
  contact_sheet.jpg          # human review grid
  tiktok_carousel.zip        # export artifact
  manifest.json              # content_id, gate results, sha256 per file
receipts/content.jsonl       # append-only: built → reviewed → publish → measured
store/aoc.db                 # SQLite: lifecycle state + acquisition garden
```

Campaign index: `store/campaigns.json` maps segment → built content_ids
for measure/learn passes. Legacy IDs resolve via `core/legacy.py`.

## Campaigns vs outcomes (the loop)

```
BUILD      run_carousel() → gated ZIP + receipts + DB rows
MEASURE    aoc_measure(post_url, metrics, namespace) → snapshot + memory
LEARN      aoc_learn(namespace) → ranked patterns by leads
MUTATE     next batch copies top-ranked hooks/angles, kills losers
```

Rules:
1. Snapshots append, never overwrite. Current totals = latest observation.
2. Rank by leads → sales, never views. A 20k-view/1-lead deck loses to a
   5k-view/4-lead deck — demonstrated in `core/memory.py` tests.
3. Namespaces isolate business lines (`aionboard` vs `powthings`).
   Plant-lover learnings never train trades content or vice versa.
4. Unattributed conversions are reported apart, never guessed into a campaign.
5. Enquiry ≠ qualified conversation (independent `qualifications` event).
6. One variable per test or the learning is noise.

## Using it for the next run

```bash
# 1. what won last time?
python3 mcp_server.py aoc_rank '{"metric": "leads", "namespace": "aionboard"}'
# 2. build mutations of the top hook (new angle, same structure)
python3 mcp_server.py aoc_build '{"hook": "<winning hook, reworded>", "segment": "nails"}'
# 3. review, post manually, then record reality:
python3 mcp_server.py aoc_metrics '{"post_url": "<tiktok url>", "content_id": "<id>", "metrics": {"views": 1200, "saves": 60, "leads": 2}, "namespace": "aionboard"}'
# 4. close the loop:
python3 mcp_server.py aoc_learn '{"namespace": "aionboard"}'
```

Fictional/demo numbers are marked as such and never mixed with measured rows.
