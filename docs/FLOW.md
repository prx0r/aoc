# FLOW — the full campaign flow, start to finish

Every command below is executable as written. Interfaces that exist:
`python -c` snippets, `mcp_server.py` (CLI + stdio), `web.viewer`.
There are no `slides.generate --hook` / `render.slideshow` / `core.review`
CLI modules — any doc showing them is stale.

## 0. Prereqs

- Website + booking link working (do not spend before this).
- Direct calls running as £0 control; log objections.
- No secrets needed for organic. R2 backup needs `.env` (gitignored).

## 1. Campaign — create and link

```bash
python3 mcp_server.py aoc_campaign \
  '{"campaign_id":"nails-launch-01","segment":"nails","offer_id":"muse-quickstart",
    "hypothesis":"question hooks beat product hooks for saves",
    "budget_gbp":0,"channel":"tiktok"}'
```

Rules enforced: no duplicate ids, known segment + offer only. Link creatives
only after approval (`link_creative` refuses unapproved revisions).

## 2. Generate — build gated carousels

```bash
python3 -c "
from core.carousel import run_carousel
r = run_carousel('Nail techs — DMs at midnight, booking at 9pm?',
                 'opportunity', segment='nails')
print(r['zip'])"
# store/AOC-XXXXXXXX/tiktok_carousel.zip
```

Or per-business variants (consent-gated):
```bash
python3 mcp_server.py aoc_personalize \
  '{"hook":"Quiet week? Fill it.","segment":"nails","business":"...","company_number":"...","area":"..."}'
```
(Short hooks only — the render-legible gate caps slide 1 at 12 words,
business name included.)

Cheap pre-check without rendering:
```bash
python3 mcp_server.py aoc_validate '{"hook":"...","segment":"nails"}'
```

## 3. Review — human gate

```bash
python3 -m web.viewer  # http://127.0.0.1:8798/ — gallery, queue, sign-off forms
```

Or via MCP: `aoc_review` (auto checks) → inspect contact sheet →
`aoc_signoff` with decision + reason. Approval binds exact asset hashes;
any re-render invalidates it.

## 4. Post — manual, always

```bash
python3 mcp_server.py aoc_publish '{"content_id":"AOC:<full-id>","platform":"tiktok"}'
# → ZIP path + contact sheet + caption + CTA + hashtags (segment tags lead,
# channel suggestions follow) + checklist
```

Upload the ZIP as a TikTok Photo Mode carousel (swipeable, NOT Template
auto-play). Pick trending sound in-app. Caption ≤150 chars + 3–5 hashtags.
Then confirm with the real URL:

```bash
python3 mcp_server.py aoc_publish_confirm \
  '{"content_id":"AOC:<full-id>","platform":"tiktok",
    "post_url":"https://www.tiktok.com/@you/video/123","account":"@you"}'
```

Refused without prior approval of that exact revision.

## 5. Measure — snapshots, never overwrites

```bash
python3 mcp_server.py aoc_metrics \
  '{"post_url":"https://www.tiktok.com/@you/video/123",
    "content_id":"AOC:<full-id>",
    "metrics":{"views":1200,"saves":60,"leads":2}}'
# Or bulk: import_studio_csv() on a TikTok Studio export.
```

Leads → qualifications → conversions are separate events
(`record_lead/qualification/conversion`), joined by campaign id.
Enquiry ≠ qualified; unattributed revenue reported apart, never guessed.

## 6. Learn — mutate winners

```bash
python3 mcp_server.py aoc_rank '{"metric":"leads","namespace":"aionboard"}'
python3 mcp_server.py aoc_learn '{"namespace":"aionboard"}'
```

Rank by leads → sales, never views. Generate mutations of top-2 hooks
(same angle, new wording), kill losers. Namespaces isolate business lines
(`aionboard` vs `powthings` vs `garden`).

## 7. Funnel — read the business

```bash
python3 mcp_server.py aoc_funnel '{"campaign_id":"nails-launch-01"}'
# → leads, qualified, paid, revenue_gbp, unattributed_paid
```

## Identity throughout

One content_id (`AOC:<64hex>`) from plan → manifest → receipt → approval →
publish → observations. See `docs/IDENTITY.md`. Resolve IDs from manifests,
never memory, never hook prefixes.
