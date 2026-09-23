# MONETIZATION — how slideshow attention becomes revenue (and what doesn't)

Research synthesis, Sep 2026. Vendor blogs conflict on platform payouts;
treated as unreliable below. What follows is the honest map.

## The one fact that sets strategy

TikTok's Creator Rewards requires 10k followers + 100k 30-day views + videos
over 1 minute — and explicitly **excludes Photo Mode** per TikTok's own
eligibility rules (openclip.app, citing official docs + quality guidelines
listing 'slide videos' as ineligible). One vendor blog (Reelbase) claims the
opposite — 3x RPM for Photo Mode — and another (SlideStorm) claims full
eligibility. They can't all be right. **Plan as if slideshows earn $0 per
view.** If Rewards ever pays on carousels, it's a windfall, not the model.

Slideshow views are a traffic asset, not a payout asset. Every route below
converts attention some other way.

## The lanes, ranked for AI Onboard

| Lane | Math (honest) | Fits AIO? |
|---|---|---|
| **Own service via bio/DM** | 0.2–0.5% of viewers hit bio link; you keep 100% margin + the relationship | ✅ THE lane. £499 setup, DM keyword CTA |
| Shop affiliate (others' SKUs) | 5–20% commission; 100k views → ~30 sales → ~$112 on $25 product. Volume game: 3–5 posts/day | ❌ no — sells tools, not setups |
| Brand deals | $100–500/post at 20–50k niche followers; inbound after organic tags perform | later — needs audience first |
| Digital products | 70–95% margin; $9–29 sweet spot; $17 PDF × 2% of 50k views ≈ $1k/mo | maybe — checklist/price-book PDF as lead magnet, not revenue |
| Creator Rewards | $0.40–1.00/1k views on 1-min+ video only; slideshows excluded (see above) | ❌ wrong format |

## What the winners actually do (consensus across 8 sources)

1. **80/20 split** — 80% pure value, 20% product-integrated. Posting all-promo
   gets classified promotional and reach dies. Our templates already do this
   (opportunity/faq/demo = value; close slide = the 20%).
2. **Saves > views.** Save rate is the strongest quality signal and the best
   public proxy for completion. Our `save_rate` derived metric exists for this.
   Checklist decks (`save this before you pay…`) are save-bait by construction.
3. **Rank by demos, not views.** Slidetik: a 4k-view deck that booked 3 demos
   beat a 20k-view deck that booked zero. Our `memory.py` already ranks by
   leads → sales. Do not regress to view-chasing.
4. **Comparison captures intent.** Buyers choosing between options (Tradify vs
   us, deposits vs no-shows) convert best — affiliate intent peaks at comparison.
   Our `comparison` template is the money template; keep it honest.
5. **One variable per test.** Hook OR proof order OR CTA — otherwise you learn
   nothing. `aoc_learn` assumes this; mixed tests corrupt learnings.
6. **Comment-bait deliberately.** Question slides ("which gap first?") at 5–8%
   comment rate lift distribution. Our diagnostic/question hooks do this.
7. **Series compounding.** "Part 1/5" chains raise session time; algorithm
   rewards bingeable accounts. Future: 5-part series per segment.
8. **Realistic timeline.** Months 1–2 ≈ £0 (testing formats). Month 3–6:
   first qualified conversations. Anyone quoting five figures is selling a course.

## AI Onboard funnel math (hypotheses, not promises)

- 500k-view slideshow → 1,000–2,500 bio visits (0.2–0.5%) → DM conversations
  at whatever our reply rate is → £499 closes at our close rate.
- We don't know reply rate or close rate yet. First 10 posts exist to measure
  the top of this funnel, not to revenue-spike.
- Founding £299 × 3 exists to buy the first verified numbers (delivery time,
  reply rate, close rate) — then the math above becomes measured, not modeled.

## What NOT to do

- Don't plan revenue around Creator Rewards for carousels (excluded format).
- Don't run affiliate SKUs on this account (dilutes the £499 offer, trains
  the algorithm on the wrong audience).
- Don't buy followers/likes (distorts the metrics the whole loop depends on).
- Don't split early volume across 9 niches (targets.md says validate one
  vertical's unit economics first — electricians, then beauty).
