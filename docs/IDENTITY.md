# IDENTITY — how one creative stays itself end to end

Four IDs, one chain. Verified live 2026-09-23 (3 fresh ads + revision test).

## The chain

```
plan.content_id  →  manifest.content_id  →  receipt.data.content_id
     (AOC:<64hex> of hook+CTA+caption+skin+renderer+offer)
       →  approval receipt (binds ZIP+slide hashes)
         →  publish_confirm (requires post_url + matching approval)
           →  observations (keyed by post_id + content_id)
             →  leads → qualifications → conversions (joined, never guessed)
```

Each link verified: plan id == manifest id == receipt id; final_cta ==
requested CTA verbatim; approval hash == disk hash; revision (new CTA) mints
a new ID the old approval cannot authorize (tested refusal).

## Known traps (all hit during verification)

1. **Hook-prefix matching is not identity.** Two builds shared
   "Cleaners: before" — tooling that matches on prefix signs the wrong one.
   Always resolve full IDs via manifest scan (`_resolve_build`).
2. **Resolvers must fail clean.** `_resolve_build("")`/`None` now raises
   `ValueError("content_id required")` instead of TypeError.
3. **Fictional demos pollute real state.** Demo posts flip content_state;
   revert to `in_review` afterwards. Receipts stay (append-only, labeled).
4. **Metrics ≠ funnel.** `aoc_metrics` records observations; `aoc_funnel`
   counts lead/qualification/conversion events. A post with 3 leads in its
   metrics dict still shows funnel zeros until lead events exist — correct,
   not a bug.
