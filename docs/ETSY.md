# ETSY — listing images, videos, and upload path

Sources: Etsy Help (images help/115015663347, video help/360053206073),
Etsy Open API v3 docs, plus third-party guides cross-checked Sep 2026.
Etsy controls the rules; recheck Help pages when the editor disagrees.

## 1. Image specs (what Etsy wants)

| Slot | Spec |
|---|---|
| Listing photos | ≥2000px both dims (short side), JPG/PNG/GIF/HEIC, sRGB, ≤10MB practical (20MB max), **up to 10 per listing** |
| First photo | ≥635×635px or lower search placement; horizontal or square; auto-cropped to 570×570 thumbnail |
| Crop reality | 4:3 desktop search, 3:4 mobile, 1:1 shop page — one image must survive all three |
| Recommended master | **2400×2400 square**, critical content inside centered **~1517×1780 safe zone**, subject centered, text ≥400px from edges |
| Shop banner | 3360×840 (4:1), critical content in middle 70% |
| Shop icon | 500×500, legible at ~40px |

Key rule: shoot wide, center subject, export sRGB, test on real devices.
No device-specific uploads exist — one square + safe zone covers everything.

## 2. Video specs (what Etsy wants)

| Rule | Value |
|---|---|
| Count | up to 2 per listing |
| Duration | **5–15s** (Help pages disagree 3–15 vs 5–15; 5–15 satisfies both) |
| Size | ≤100MB |
| Format | MP4 (H.264 preferred) or MOV |
| Resolution | ≥1080px shortest side; 1:1 square best, 9:16 also accepted |
| Audio | **stripped on upload** — design silent (text overlays carry the message) |
| Sweet spot | 8–12s, 3–4 scenes, smooth cross-fades, product visible in first 3s |

## 3. What aoc generates today vs the gap

| Need | Today | Gap |
|---|---|---|
| 1080×1920 TikTok PNGs | ✅ `render/slide.py` | — |
| 2400×2400 Etsy square + safe zone | ❌ | **`render/etsy.py: render_square()` (this spec builds it)** |
| 5–15s silent MP4 from slides | ❌ | **`render/etsy.py: render_video()` via ffmpeg (this spec builds it)** |
| Listing copy (title/desc/13 tags) | ✅ `segments/*/etsy/*.md` | validate tag length ≤20 chars |
| 10-slot photo plan per product | ❌ | packet builder (below) |
| Upload | manual | API draft path spec'd (§5), not built |

## 4. Listing packet (per product)

10 photo slots: 1 hero (square, product centered) · 2–3 lifestyle/context ·
1 scale (size reference) · 1 detail/close-up · 1 packaging/what's-included ·
1 proof (sensor readout, review, process) · 1 gift angle · 1 shop-card/brand ·
1 video (8–12s silent slideshow). Plus title (≤140 chars), description,
13 tags (≤20 chars each), materials, taxonomy id. Copy lives in
`segments/<id>/etsy/<product>.md`; the packet assembler validates lengths.

## 5. Upload path (manual now, API-shaped later)

Manual today: Shop Manager → Listings → Photos and video → drag/drop →
thumbnail tool check → publish. Matches house doctrine (no auto-post).

API later (spec, not code): Etsy Open API v3 OAuth 2.0 + PKCE on localhost
(pattern: Contentsy — Flask, `listings_r listings_w shops_r`, redirect
`http://127.0.0.1:5050/etsy/callback`), `createDraftListing` →
`uploadListingImage` × N → optional video → `updateListing(state=draft)`.
Drafts only — activation stays a human click. Python SDK reference:
`amitray007/etsy-python-sdk` (`ListingImage`/`ListingVideo` resources);
MCP reference: `jeffkimble/etsy-mcp-server-gen` (16 tools). Avoid
cookie-scraping approaches (`robomello/etsy-browser` style): ToS risk,
conflicts with the trust model.

## 6. Review additions for Etsy outputs

- Square: subject centered, text inside safe zone, ≥2000px, sRGB, ≤10MB.
- Video: 5–15s, ≤100MB, silent-legible (message works muted), product in
  first 3s, no audio-dependent claims.
- Copy: title ≤140 chars, 13 tags ≤20 chars each, no validated-cost or
  waterproof claims (existing gates already refuse these).

## 7. Phases

1. ✅ Spec (this file). 2. Square renderer + tests. 3. Silent MP4 exporter
+ tests. 4. Packet assembler + per-product packets for 4 heroes.
5. API draft integration (needs Etsy app + OAuth — human step).
