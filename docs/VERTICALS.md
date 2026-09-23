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

## Skin contract (all 13)

`segments/<id>/{profile,hooks,proofs,templates,manifest}.yaml` +
`PAINS.md` + `CAMPAIGN.md`. Engine falls back: explicit hand-tuned decks →
generic skin-driven decks → refuse (never another trade's copy).

## Prices

Niche test prices (£249–£699) are hypotheses until validated (targets.md).
Standard £499 + £299 founding is the fallback close. Closes carry pilot
wording where the niche price is unvalidated.
