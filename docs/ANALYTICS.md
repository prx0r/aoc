# ANALYTICS — what we pull, where from, what it means

## The honest stack

Watch time and completion rate are NOT in any public API. Proxies only:
- **Save rate** (`collect_count`/views) — best public proxy for completion.
  A bookmark means they watched enough to want to return.
- **Engagement velocity** — (likes+comments+shares)/views, bucketed; ranks within bucket.
- **Per-bucket regression** — needs YOUR Creator Studio CSV joined on post id.
  Fit once, score competitors with the same coefficients.

## Sources, in order of access

| Source | Needs | Gives | Status |
|---|---|---|---|
| Manual entry | nothing | whatever you type | ✅ `aoc_metrics` live |
| Studio CSV export | TikTok Studio access | views/likes/comments/shares/saves per post | ✅ `import_studio_csv` live |
| Display API `/v2/video/list`,`/query` | OAuth on own account | own posts: views/likes/comments/shares/saves | documented, not wired |
| Business API `identity/video/info` | advertiser auth | CAROUSEL item_type + carousel_info | documented, not wired |
| Public scrapers | third-party key | any public post counts (no watch time) | documented, not wired |

## Rules

1. Snapshots append, never overwrite (`receipts/metrics.jsonl`). Raw rows keep
   timestamps so deltas and growth rates recompute any window.
2. Derived metrics compute from raw: engagement_rate, save_rate, share_rate,
   comment_rate, profile_rate, cpqc, cpsc. Platform average 3.85–4.90%;
   >5% strong, >10% viral-potential.
3. Rank creatives by **leads → sales → saves**, never views. A 20k-view deck
   with zero demos lost to a 4k-view deck with three.
4. `aoc_learn` compiles snapshots into `memory.json` (best hooks/times/styles).
   Before generating, read learnings and mutate winners.
5. Change ONE variable per test (hook OR proof order OR CTA) or you learn nothing.

## What /content does vs aoc

/content `measure(video_id, metrics)` records whatever dict you pass into the
receipt chain — no fetching, no derived rates, no learnings compiler, no CSV
import. AOC keeps the receipt-compatible shape and adds the other three layers.
Same refusal philosophy: no invented numbers in, no phantom precision out.

## Current state

Zero posts measured — the loop is armed, unfired. First action after posting:
export Studio CSV → `import_studio_csv` → `aoc_learn` → mutate winners.
