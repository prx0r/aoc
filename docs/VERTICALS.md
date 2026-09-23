# VERTICALS — aoc segments × aionboard packs

AOC is the marketing arm: every aionboard vertical gets a content skin with
the same offer pointer, same exclusions, same contact rules. When OFFER.md
changes, skins change — automation never outruns the offer.

| aoc segment | aionboard vertical(s) | Pack | Prospects |
|---|---|---|---|
| electrician | electrician | full (PAINS→INSTALL) | prospects_electrical.csv (10k) |
| beautician | beauty (+nails, lashes, hair) | full | social/directories (no CH list) |
| nails | nails | full | TikTok/IG/directories |
| lashes | lashes | full | IG/TikTok/booking platforms |
| hair | hair | full | IG/FB/directories |
| cleaners | cleaners | full | FB groups/Maps |
| dog_groomers | dog-groomers | full | FB/Maps/directories |
| gardeners | gardeners-window-cleaners | full | Maps/directories/FB |
| car_detailers | car-detailers | full (stub pains) | IG/TikTok/Maps |
| driving_instructors | driving-instructors | full (stub pains) | Maps/directories |
| weddings | weddings | full (stub pains) | IG/marketplaces |
| plumber | — (aoc-original, VISION-sourced) | none | — |
| sole_trader | — (aoc-original, VISION-sourced) | none | — |

## Skin contract (13 trade skins + powthings + garden_familiars = 15)

`segments/<id>/{profile,hooks,proofs,templates,manifest}.yaml` +
`PAINS.md` + `CAMPAIGN.md`. Engine falls back: explicit hand-tuned decks →
generic skin-driven decks → refuse (never another trade's copy).

## Plus: powthings (separate business line)

POW physical AI companions — plant/clock/coffee/guitar owners, gift buyers.
Own skin, own `powthings-preview` offer (unavailable, launch list only),
own memory namespace. Audiences must never cross-train learnings.

## Prices (two-tier since Sep 2026)

- Five wedges (nails, lashes, hair, cleaners, car_detailers, gardeners):
  **£20 assisted Muse setup** + 7 days support + personalised manual.
  Muse is US-only, no confirmed UK date: build the UK waiting list now,
  take £20 only when the customer can access the features.
- Electrician: separate higher-value POW route, **£499** standard setup.
  Never force complex quoting/compliance into the £20 product.
- Older niche test prices (£249–£699, targets.md) are superseded for wedges;
  retained in proofs as hypotheses where still referenced.
