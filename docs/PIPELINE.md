# PIPELINE — how to run the £100 experiment with AOC

> Mechanics live in `docs/FLOW.md` (every command executable). This doc is
> the experiment plan: what to build, what to spend, what to kill.

## 0. Prereqs
- Website + booking link working (do not spend before this).
- Direct calls running as £0 control; log objections.

## 1. Generate (free, local)
```bash
cd /root/aoc
python3 -c "
from core.carousel import run_carousel
r = run_carousel('UK electricians — still doing quotes at 9pm?', 'opportunity')
print(r['zip'])"                    # store/AOC-XXXXXXXX/tiktok_carousel.zip
python3 -m pytest tests/ -q         # 90 passed
```
Make 10–15 across templates: opportunity ×4, before_after ×3, faq ×2, demo ×2, social_proof ×2.
Each with 2 hook variants (see segments/electrician/hooks.yaml).

## 2. Review (human gate)
- Open JPEGs in `store/AOC-XXXXXXXX/` (or the gallery: `python3 -m web.viewer`). Check: buyer identified slide 1? One idea per slide?
  Claim in proofs.yaml? CTA present?
- Move `draft → in_review → approved|rejected` in `core/state.py` terms. Rejected → back to draft with reason.

## 3. Post (manual)
- TikTok: upload PNGs as photo carousel, pick trending sound in-app, add hashtags from
  channels/tiktok.yaml manually. Check audience geography after 48h.
- Cross-post winners to Instagram + Facebook organic (reuse same ZIP).

## 4. Measure
```python
from core.memory import record
record("receipts/memory.json",
  {"audience":"owner_2_10","hook":"quotes at 9pm","angle":"pain_callout","slide_count":7,"cta":"DM QUOTE","visual_style":"dark"},
  {"views":1200,"swipes":300,"profile_visits":40,"clicks":12,"leads":3,"sales":1,"spend_gbp":0})
```
- Organic: leads/sales per creative. Paid (£70 FB): cost per qualified conversation first.

## 5. Learn
- `aoc_rank` (MCP) or `core/memory.py:rank()` sorts by leads, not views.
- Generate mutations of top-2 by leads: same angle, new hook wording / slide count / CTA.
- Kill declarative product hooks if question hooks win (expected per research).

## 6. Spend (£70 + £30)
- £70 Facebook: 1 offer × 2 creatives (best 2 organic winners), qualification question on form.
- £30 reserve: extend winner or TikTok Promote if UK targeting available.
- Never auto-post. Never split £100 three ways.

## Query from powops/agents (MCP stdio)
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 mcp_server.py
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"aoc_status","arguments":{}}}' | python3 mcp_server.py
```
Tools: full 20 (see README + `docs/FLOW.md` for the campaign→funnel flow).
