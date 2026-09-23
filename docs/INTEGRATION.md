# INTEGRATION — aionboard × powrobots × aoc × fal.ai × etsy

## The two businesses

### aionboard — AI setup services
- **What**: Free demo → £20 basic setup → £50/mo integrated
- **Who**: UK trades (electricians, cleaners, gardeners, beauty, etc.)
- **How**: TikTok carousels → DM DEMO → 20-min call → workflow configured → £20
- **Repo**: `/root/aionboard` (offer, trust model, 11 verticals)
- **Ad factory**: `/root/aoc` (20 MCP tools, 16 segments, free demo funnel)

### powrobots — physical creature companions
- **What**: Glimlings — tiny magical creatures that inhabit everyday objects
- **Who**: Plant lovers, gift buyers, desk collectors, families
- **How**: TikTok carousels → DM GLIMLING → waitlist → pre-order → ship
- **Repo**: `/root/powrobots` (brand, 8 characters, 6 product lines, SCAD enclosures)
- **Ad factory**: `/root/aoc` (glimlings segment, gen art, free demo CTA)

## The integration map

```
                    ┌─────────────────┐
                    │   fal.ai        │
                    │ (image gen)     │
                    │ $0.003/img      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ aoc      │  │ aoc      │  │ etsy     │
        │ (TikTok) │  │ (TikTok) │  │ (shop)   │
        │ aionboard│  │ powrobots│  │ powrobots│
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │
             ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ DM DEMO  │  │ DM GLIM  │  │ BUY NOW  │
        │ → £20    │  │ → waitlist│  │ → £15-119│
        └──────────┘  └──────────┘  └──────────┘
```

## Revenue streams

| Stream | Product | Price | Channel | Funnel |
|--------|---------|-------|---------|--------|
| aionboard services | AI setup | £20-50/mo | TikTok → DM DEMO | Free demo → configure → pay |
| powrobots physical | Glimlings | £15-119 | TikTok → DM GLIMLING | Waitlist → pre-order → ship |
| powrobots etsy | Digital prints | £5-15 | Etsy → download | Browse → buy → instant delivery |
| powrobots etsy | Physical toys | £25-79 | Etsy → ship | Browse → buy → 3D print → ship |

## fal.ai integration (high-quality images)

### Cheapest: FLUX.1 [schnell] — $0.003/megapixel
- 1024×1024 = $0.003 (one third of a cent)
- 1000 images = $3
- Best for: bulk product photos, ad variants, A/B testing

### Mid-range: FLUX.2 [dev] Turbo — $0.008/image
- Higher quality, slower
- Best for: hero images, Etsy listings, final outputs

### Premium: Nano Banana 2 — $0.08/image at 1K
- Best quality, highest price
- Best for: hero product shots, brand campaigns

### Recommended pipeline
```
1. Generate 10 variants with schnell ($0.03)
2. Pick best 2
3. Regenerate with dev Turbo for final quality ($0.016)
4. Total cost per listing: ~$0.05
```

## Video generation (Etsy listings)

### Options
| Model | Price | Quality | Speed |
|-------|-------|---------|-------|
| fal.ai WAN 2.2 | ~$0.05/video | Good | Fast |
| fal.ai MiniMax | ~$0.10/video | Better | Medium |
| TikTok native | Free | Good enough | Manual |

### Video use cases
1. **Etsy listing video**: 10s product rotation showing creature from angles
2. **TikTok ad**: 15s before/after with creature animation
3. **Instagram Reel**: 10s "unboxing" style reveal
4. **Website hero**: 5s creature animation on landing page

### Recommended: Start with stills, add video later
- Etsy allows 1 static image + 1 video per listing
- Static images are cheaper and faster to produce
- Video adds ~20% conversion lift on Etsy (industry data)
- Start with 5 images per listing, add video when profitable

## Content strategy per platform

### TikTok (aoc handles both)

**aionboard ads:**
- Format: before/after, trust, FAQ
- CTA: "DM DEMO for a free 20-min setup"
- Hook: pain-first ("Quotes at 2pm, not 9pm")
- Segments: electrician, cleaners, gardeners, beauty

**powrobots ads:**
- Format: story, comparison, character intro
- CTA: "DM GLIMLING for launch updates"
- Hook: creature-first ("Meet Mosswick, guardian of tomatoes")
- Segments: glimlings, garden_familiars, powthings

### Etsy (powrobots only)

**Digital prints:**
- 5 images per listing: hero, detail, lifestyle, scale, packaging
- SEO-optimized titles: "Glimling Mosswick — Garden Spirit Digital Print"
- Tags: glimling, plant spirit, cottagecore, digital print, woodland creature

**Physical toys (when ready):**
- 5 images: front, side, back, scale, packaging
- 1 video: 10s rotation
- Price: £25-79 depending on line
- Shipping: UK only initially, international later

### Instagram (cross-post winners)

- Reuse TikTok winners as Reels
- Add carousel posts for product showcases
- Stories for behind-the-scenes (3D printing, packaging)

## fal.ai integration in aoc

### Current state
- `core/images.py` generates via Cloudflare Workers AI (lightning model)
- ~$0.00 per image (free tier)
- Quality: good for ad backgrounds, not for hero product shots

### Upgrade path
1. **Phase 1** (now): Cloudflare lightning for ad backgrounds — free
2. **Phase 2**: fal.ai schnell for bulk ad variants — $0.003/img
3. **Phase 3**: fal.ai dev Turbo for Etsy listings — $0.008/img
4. **Phase 4**: fal.ai Nano Banana for hero shots — $0.08/img

### Implementation
```python
# core/images.py — add fal.ai provider
FAL_MODELS = [
    ("fal-ai/flux/schnell", "schnell"),      # $0.003/MP — bulk
    ("fal-ai/flux/dev", "dev-turbo"),         # $0.008/img — quality
    ("fal-ai/nano-banana", "nano-banana"),    # $0.08/img — hero
]

def generate(prompt, out_name, model="schnell"):
    # fal.ai API call
    # save to assets/photos/
    # append sources.json
```

## 3D printing pipeline (powrobots)

### SCAD templates ready
- mushroom.scad, frog.scad, ghost.scad, goblin.scad, mood.scad, weather.scad
- Parametric: engine, product, character, colour, dimensions
- JLC3DP MJF Nylon production

### Etsy listing workflow
1. Generate creature art with fal.ai
2. Create 3D model from SCAD template
3. Print via JLC3DP or local printer
4. Photograph (or render) from multiple angles
5. Create Etsy listing with 5 images + video
6. Ship to customer

### Digital products (no printing needed)
1. Generate creature art with fal.ai
2. Create print-ready files (300 DPI, various sizes)
3. Upload to Etsy as digital download
4. Customer prints at home or at print shop
5. Zero marginal cost per sale

## Priority order

### Week 1-2: Get aionboard ads running
- [x] Free demo funnel built
- [ ] Post 3 TikTok carousels
- [ ] Measure DMs + demo bookings
- [ ] Iterate hooks from data

### Week 3-4: Get powrobots ads running
- [ ] Character intro decks built
- [ ] Post 3 TikTok carousels
- [ ] Measure DMs + waitlist signups
- [ ] Iterate hooks from data

### Week 5-6: Etsy listings
- [ ] Generate 5 product images per Glimling with fal.ai
- [ ] Create 5 Etsy listings (digital prints)
- [ ] Add to Etsy shop
- [ ] Measure views + favourites + sales

### Week 7-8: Scale what works
- [ ] Double down on winning hooks
- [ ] Add video to top-performing listings
- [ ] Cross-post to Instagram
- [ ] Start £70 Facebook test on winners

## Budget

| Item | Cost | Notes |
|------|------|-------|
| TikTok ads | £0 | Organic posting only |
| fal.ai images | ~$5/mo | 1000 images at $0.003 each |
| Etsy listing fees | £0.20/listing | 5 listings = £1 |
| Etsy transaction fee | 6.5% | On sales only |
| Facebook test | £70 | Week 7-8, winners only |
| 3D printing | TBD | JLC3DP quote per batch |
| **Total month 1-6** | **~£75** | Mostly time, very little cash |

## Key insight

Both businesses sell the same thing: **AI that feels like magic**.
- aionboard: "Your assistant is already working, you just haven't met it yet"
- powrobots: "Your desk is already alive, you just haven't named it yet"

The creature (Glimling) is the mascot for both. Mosswick watches your plants AND
sets up your AI workflow. Puck runs your spreadsheets AND glows on your desk.
The brand is one story: tiny magic that solves real problems.
