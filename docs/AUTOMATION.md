# AUTOMATION — per-business carousels without breaking the rules

## What "automate for each business" means here

Three separate jobs, three different risk levels:

| Job | What | Risk | Status |
|---|---|---|---|
| **Score** | rank 10k prospects → top-N by CSV fields | none (read-only) | ✅ `core/personalize.top_prospects`, MCP `aoc_score` |
| **Personalize** | per-business hook variant (identity tokens only) | medium (identity must be real) | ✅ `variant_spec` + `personalization-v1` gate |
| **Deliver** | attach variant to 1-to-1 follow-up | HIGH (compliance) | 🔒 gated: research-only default, consented only post-call |

What we do NOT automate: sending. No bulk outreach, no auto-DMs, no auto-email.
Per aionboard contact rules: verify source, record basis, TPS/CTPS screen,
never market to research records automatically.

## The pipeline

```
prospects_electrical.csv (10k rows)
  → top_prospects(limit, min_score)      # density + sic diversity; age unknown flagged
  → variant_spec(row, hook, template)    # "GALLOWAY GROUP (G2) — still doing…?"
  → run_variant()                        # 6 gates incl. personalization-v1
  → store/<content_id>/ + receipt        # stamped research-only
  → (human call happens)
  → status → consented → attach to day-1 follow-up (market intel report + carousel)
```

## Token law

Allowed: `{business_name}`, `{area}`, `{service}` — all from CSV columns.
Forbidden: numbers, claims, outcomes, first names. The gate refuses
`{first_name}`, `{amount}`, or any unknown token. Business name without
company_number is refused (untraceable prospect).

Identity goes on slide 1 and nowhere else. Stats stay segment-level
from `proofs.yaml`. A variant never claims "you lose £X" — only "you, in {area}".

## Scoring honesty

CSV has no incorporation dates and no hiring signals, so HOT (80+) is
unreachable by automation — documented in the score as `age_unknown: True`
with `priority_note`. Top of the automated ranking ≈ high-WARM. HOT requires
a human to verify CH age + hiring + contact source. The score says so.

## Outreach pairing (sales playbook)

- Day 0 call (consented context established) → generate variant → attach to
  day-1 follow-up email alongside the market intel report (3 planning apps etc).
- Demo leave-behind: variant with the prospect's trade + area as the opener.
- Organic segment carousels keep running in parallel (marketing, not 1-to-1).

## Segment manifests

`segments/<id>/manifest.json` mirrors aionboard `verticals/<id>/manifest.json`:
same `pilot_package`, same `excluded_from_standard_pilot`, same contact rules,
`public_offer` pointing at `/root/aionboard/OFFER.md`. When OFFER.md changes,
skins change — automation never outruns the offer (see scope fix Sep 23:
voice/WhatsApp/website claims removed same session OFFER.md landed).
