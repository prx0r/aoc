# HANDOVER — /root/aoc

_Last updated: 2026-09-23. This is the operational handover for the next agent._

## One-line status

`aoc` is a real, deterministic TikTok/Pinterest-style carousel factory with
receipts, gates, review, campaign records, local assets, and a tested MCP/CLI
surface. It is **not yet a validated advertising business**: the current local
database has zero real posts, observations, leads, qualifications, or conversions.

## Current numbers

- 16 segment skins.
- 20 MCP tools exposed by `mcp_server.py`.
- 99 automated tests pass locally; seven Pillow deprecation warnings remain.
- 182 build manifests, 177 contact sheets, and 182 ZIP artefacts in ignored
  `store/`; receipts are ignored, append-only, and hash-chained.
- Local database: campaigns and linked creatives exist; `posts=0`,
  `observations=0`, `leads=0`, `conversions=0`.
- All segment hook banks now have at least 10 hooks; the latest 20-hook
  expansion is commit `e649481` locally and is not yet on origin.

## What actually works

### Content production

```text
hook + template + segment
  -> plan
  -> proof resolution
  -> 9 fail-closed gates
  -> PIL/Montserrat render
  -> pixel validation
  -> review manifest/contact sheet
  -> human sign-off bound to exact hashes
  -> ZIP publish packet
```

- `core/carousel.py` is the orchestrator.
- `render/slide.py` is the local deterministic renderer.
- `segments/*/` contains the copy, proofs, templates, pains, and campaign data.
- `core/images.py` serves pinned local photos and can call Cloudflare Workers
  AI when credentials are present.
- `core/gradients.py` contains a curated uiGradients collection, but it is
  **not wired into the renderer yet**.
- `core/etsy_packet.py` can create listing packets, but it does not upload to
  Etsy and real product photography is still missing.

### Campaign/receipt machinery

- `aoc_campaign` creates campaign records.
- `link_creative` links approved creatives.
- `aoc_publish` returns a manual-pending packet with ZIP, CTA, caption,
  hashtags, sound guidance, photo attribution, and checklist.
- `aoc_publish_confirm` requires a real post URL and an exact approved revision.
- `aoc_metrics` and the acquisition tables support post-level observations,
  leads, qualifications, conversions, and funnel reporting.
- No auto-post tool exists; this is intentional.

### Verified local integrations

- R2 backup was tested with a real upload and verify-after-write path.
- Cloudflare image generation was tested directly with Workers AI credentials;
  generated Puck/Mosswick assets and attribution records exist locally.
- GitHub remote is `https://github.com/prx0r/aoc.git`.

## What is not working or not proven

1. **No distribution proof.** Nothing has been posted to TikTok or any social
   platform. Campaign records and zero funnels are not revenue evidence.
2. **Free demo is an experiment, not an upstream offer.** `offers.yaml:8`
   defines a local `free-demo` offer, but it is not present in the canonical
   `aionboard/OFFER.md`; treat it as a hypothesis until the offer owner approves it.
3. **Caption metadata bug.** `core/channels.py:105` appends `DM DEMO or link
   in bio` to every TikTok caption, including Glimlings and non-demo offers.
   It also merges generic electrician tags into Glimlings packets. Fix before
   publishing those packets.
4. **Gradient collection is dormant.** `core/gradients.py` is not called by
   `render/slide.py`; the live renderer still uses its own accent gradients.
5. **Cloudflare generation is not a normal CLI path.** `core/images.generate`
   reads `CLOUDFLARE_API_TOKEN` and `R2_ACCOUNT_ID` from the process
   environment; it does not load `.env` itself. The direct call worked only
   when both variables were exported.
6. **Aionboard and powrobots are not code-integrated.** The repos are linked
   conceptually through `docs/INTEGRATION.md`; no shared runtime package or
   API connects them.
7. **fal.ai, Notch, Tesseract, and Etsy automation are research/plans**, not
   active aoc integrations.
8. **“Premium/amazing” is subjective.** The contact sheets are legible and
   coherent, but no external creative benchmark or performance data validates
   that description.

## First next actions

1. Fix the channel caption/hashtag metadata by campaign/segment before any
   Glimlings or paid offer packet is used.
2. Decide whether `free-demo` is an approved aionboard offer; if not, label
   it experimental or remove it from production-facing packets.
3. Manually post one approved aionboard and one Glimlings carousel using Photo
   Mode, then call `aoc_publish_confirm` with the real URLs.
4. Record real metrics and lead events. Only after that use `aoc_rank` and
   `aoc_learn` to choose winners.
5. Wire `core/gradients.py` into the renderer only after a visual A/B review;
   do not add more visual systems before distribution data exists.
6. Restore GitHub authentication, then push local commit `e649481` and the
   handover commit:

```bash
cd /root/aoc
gh auth login -h github.com
git push origin main
```

## Important commands

```bash
python3 -m pytest tests/ -q
python3 mcp_server.py aoc_validate '{"hook":"...","segment":"electrician"}'
python3 mcp_server.py aoc_build '{"hook":"...","template":"opportunity","segment":"electrician"}'
python3 -m web.viewer
python3 -m core.legacy store
```

Never commit `.env`, ZIPs, generated images, databases, or receipts. Never
invent post URLs, metrics, leads, prices, or customer outcomes.
