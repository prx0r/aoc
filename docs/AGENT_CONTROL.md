# AGENT_CONTROL — how to drive every layer of the stack

For AI agents controlling aoc programmatically. Every command is real and
tested. Copy-paste safe. No placeholders.

## Quick reference

```bash
# All MCP tools via CLI
python3 mcp_server.py <tool_name> '<json_args>'

# Python API (for agents with shell access)
python3 -c "from core.carousel import run_carousel; print(run_carousel('hook', 'opportunity', segment='electrician'))"

# Tests (always green, no network)
python3 -m pytest tests/ -q
```

---

## Layer 1: VALIDATE (cheap, no render)

Check if a hook passes all 9 gates before building.

```bash
python3 mcp_server.py aoc_validate '{"hook":"UK electricians — still doing quotes at 9pm?","segment":"electrician"}'
```

Returns: `{passed: bool, gates: {gate_name: {ok, detail}}, proof_id, evidence_refs}`

Gate names: `evidence-fresh-v1`, `no-duplicate-v1`, `claim-resolved-v1`,
`hook-quality-v1`, `render-legible-v1`, `personalization-v1`, `offer-fresh-v1`,
`offer-cta-v1`, `suppression-v1`.

Hook rules: ≤12 words, must name buyer term OR number OR question mark,
must open a loop (question/number/contrast). Bare statements are rejected.

---

## Layer 2: BUILD (render + validate + export)

```bash
python3 mcp_server.py aoc_build '{"hook":"UK electricians — still doing quotes at 9pm?","template":"opportunity","segment":"electrician"}'
```

Returns: full build dict with `out_dir`, `manifest`, `gates`, `validation`, `zip`.

Templates: `opportunity`, `before_after`, `faq`, `social_proof`, `demo`,
`diagnostic`, `teardown`, `comparison`, `annuity`, `retention`, `waitlist`, `trust`.

With photo backgrounds:
```python
from core.carousel import run_carousel
r = run_carousel("hook", "opportunity", segment="electrician", photos=True)
# r["out_dir"] = "store/AOC-XXXXXXXX/"
# r["manifest"]["photo_credit"] = "Photos: Aaron Y via Wikimedia Commons (CC BY 2.0)."
```

Output structure per build:
```
store/AOC-XXXXXXXX/
  manifest.json    # content_id, hook, template, slides, sha256, review, photo_credit
  script.json      # full plan dict (slides, segment, offer, claims)
  slide_00.jpg     # rendered JPEGs (1080x1920)
  slide_01.jpg
  ...
  contact_sheet.jpg
  tiktok_carousel.zip
```

---

## Layer 3: REVIEW (machine + human)

```bash
# Machine review (8 auto checks)
python3 mcp_server.py aoc_review '{"content_id":"AOC:XXXXXXXX"}'

# Human sign-off (writes to receipt chain)
python3 mcp_server.py aoc_signoff '{"content_id":"AOC:XXXXXXXX","decision":"approved","reason":"hook pays off, body delivers","reviewer":"agent-name"}'
```

Decision values: `approved`, `rejected`. Reason is required (free text).
Approval binds exact asset hashes — any re-render invalidates it.

---

## Layer 4: CAMPAIGN (track everything)

```bash
# Create campaign
python3 mcp_server.py aoc_campaign '{"campaign_id":"electrician-launch-01","segment":"electrician","offer_id":"muse-quickstart","hypothesis":"question hooks beat statements","budget_gbp":0,"channel":"tiktok"}'

# Link approved creative (python API — no MCP tool for linking yet)
python3 -c "
from core.acquisition import link_creative
print(link_creative('electrician-launch-01', 'AOC:XXXXXXXX'))
"
```

Campaign state lives in `store/aoc.db` (gitignored). Query:
```python
import sqlite3
conn = sqlite3.connect("store/aoc.db")
print(conn.execute("SELECT * FROM campaigns").fetchall())
```

---

## Layer 5: PUBLISH (packet → manual post → confirm)

```bash
# Get publish packet (ZIP + caption + CTA + hashtags + checklist)
python3 mcp_server.py aoc_publish '{"content_id":"AOC:XXXXXXXX","platform":"tiktok"}'

# After manual upload, confirm with real URL
python3 mcp_server.py aoc_publish_confirm '{"content_id":"AOC:XXXXXXXX","platform":"tiktok","post_url":"https://www.tiktok.com/@you/video/123","account":"@you"}'
```

Packet includes: `zip`, `contact_sheet`, `caption`, `cta`, `hashtags`,
`checklist` (includes "paste photo_credit into caption when non-empty"),
`photo_credit`.

Confirm refuses without: (1) prior approval of that exact revision,
(2) a real post_url (empty string → error).

---

## Layer 6: MEASURE (snapshots + funnel)

```bash
# Record metrics snapshot (post URL + content_id + numbers)
python3 mcp_server.py aoc_metrics '{"post_url":"https://www.tiktok.com/@you/video/123","content_id":"AOC:XXXXXXXX","metrics":{"views":1200,"saves":60,"leads":2}}'

# Record a lead event
python3 -c "
from core.acquisition import record_lead
print(record_lead('electrician-launch-01', 'AOC:XXXXXXXX', 'DM from profile visit'))
"

# Record qualification
python3 -c "
from core.acquisition import record_qualification
print(record_qualification('electrician-launch-01', 'AOC:XXXXXXXX', 'replied with area + budget'))
"

# Record conversion
python3 -c "
from core.acquisition import record_conversion
print(record_conversion('electrician-launch-01', 'AOC:XXXXXXXX', amount_gbp=499))
"

# Read funnel
python3 mcp_server.py aoc_funnel '{"campaign_id":"electrician-launch-01"}'
# → {leads: N, qualified: N, paid: N, revenue_gbp: N, unattributed_paid: N}
```

Enquiry ≠ qualified ≠ paid. These are separate events joined by campaign_id.
Never guess attribution — unattributed revenue is reported separately.

---

## Layer 7: LEARN (rank + mutate)

```bash
# Rank creatives by metric (leads, saves, views)
python3 mcp_server.py aoc_rank '{"metric":"leads","namespace":"aionboard"}'

# Generate mutation suggestions
python3 mcp_server.py aoc_learn '{"namespace":"aionboard"}'
```

Namespaces: `aionboard`, `powthings`, `garden`. Never mix.

Hook banks are the standing army:
```bash
# List hooks for a segment
python3 mcp_server.py aoc_hooks '{"segment":"electrician"}'
```

Every hook in every bank must pass gates (enforced by test).

---

## Layer 8: PERSONALIZE (per-business variants)

```bash
python3 mcp_server.py aoc_personalize '{"hook":"Quiet week? Fill it.","segment":"nails","business":"Sarah Nails","company_number":"12345678","area":"Manchester"}'
```

Consent-gated: defaults to `research-only`. Business name counts toward
the 12-word hook cap. Short hooks only.

---

## Layer 9: BACKUP (R2)

```bash
python3 mcp_server.py aoc_backup '{"content_id":"AOC:XXXXXXXX"}'
```

Uploads ZIP + manifest to `aoc-assets` R2 bucket. Verifies after write.
Logs `backed_up` receipt. Needs `R2_*` env vars.

---

## Layer 10: INSPECT + LINEAGE (debug)

```bash
# Full inspection of a build
python3 mcp_server.py aoc_inspect '{"target":"AOC:XXXXXXXX"}'

# Content lineage (receipt chain)
python3 mcp_server.py aoc_lineage '{"limit":10}'

# Raw receipt stream
python3 mcp_server.py aoc_receipts '{}'
```

---

## Layer 11: GENERATE AI ART

```python
from core.images import generate
# Cloudflare Workers AI (lightning model, ~2s, ~100KB)
p = generate("Tiny magical desk creature with acorn hat, glowing belly", "puck-gen.jpg")
# → saves to assets/photos/puck-gen.jpg, appends sources.json
```

Needs: `CLOUDFLARE_API_TOKEN` + `R2_ACCOUNT_ID` in env (see `.env.example`).

---

## Python API (for agents with import access)

```python
# Core pipeline
from core.carousel import run_carousel, plan, render
from core.gates import run_gates
from core.proof import proof_from_plan
from core.validate import validate_carousel, validate_slide, contact_sheet
from core.review import run_review

# Identity
from core.ids import content_id_for, record_id, record_short

# Campaigns + funnel
from core.acquisition import (create_campaign, link_creative,
    record_lead, record_qualification, record_conversion)

# Memory + learning
from core.memory import record, rank, learn
from core.analytics import derive, import_studio_csv

# Images
from core.images import photo_for, credit_line, generate

# Offers + claims
from core.offers import get_offer
from core.channels import channel_hashtags, channel_checklist

# Rendering
from render.slide import render_slide, render_slideshow, export_zip
```

---

## Full e2e example (one hook to tracked campaign)

```python
import json, subprocess, sys
sys.path.insert(0, ".")

# 1. Validate
subprocess.run(["python3", "mcp_server.py", "aoc_validate",
    json.dumps({"hook": "Sparkies — who answers while you are up a ladder?", "segment": "electrician"})],
    check=True)

# 2. Build
from core.carousel import run_carousel
r = run_carousel("Sparkies — who answers while you are up a ladder?",
                  "opportunity", segment="electrician", photos=True)
cid = r["manifest"]["content_id"]
print("built:", r["out_dir"], cid)

# 3. Sign off
from mcp_server import aoc_signoff
aoc_signoff(cid, "approved", "hook + body + photos verified", reviewer="agent")

# 4. Campaign + link
from core.acquisition import create_campaign, link_creative
create_campaign("sparky-test-01", "electrician", "muse-quickstart", 1,
                "test pipeline", 0, "tiktok")
link_creative("sparky-test-01", cid)

# 5. Publish packet
from mcp_server import aoc_publish
pkt = aoc_publish(cid, "tiktok")
print("zip:", pkt["zip"], "cta:", pkt["cta"], "tags:", pkt["hashtags"][:3])

# 6. After manual post, confirm + measure
# from mcp_server import aoc_publish_confirm, aoc_metrics
# aoc_publish_confirm(cid, "tiktok", "https://tiktok.com/@you/video/123", "@you")
# aoc_metrics("https://tiktok.com/@you/video/123", cid, {"views":500, "leads":1})

# 7. Funnel
from mcp_server import aoc_funnel
print(aoc_funnel("sparky-test-01"))
```

---

## State map (where things live)

| What | Where | Git | Survives |
|---|---|---|---|
| Code + skins + claims + offers | git | yes | forever |
| Build output (slides, ZIP) | `store/AOC-XXXXXXXX/` | no (.gitignore) | until pruned |
| Receipt chain | `receipts/*.jsonl` | no (.gitignore) | forever (append-only) |
| Campaigns + leads + funnel | `store/aoc.db` | no (.gitignore) | until deleted |
| AI-generated photos | `assets/photos/` | yes (gitignored *.jpg except pinned) | until deleted |
| CC photos + sources | `assets/photos/sources.json` | yes | forever |
| Env secrets | `.env` | no (.gitignore) | until deleted |

---

## Error patterns (what goes wrong and how)

| Error | Cause | Fix |
|---|---|---|
| `hook too long (N words, max 12)` | Hook exceeds word cap | Shorten. Business names count. |
| `hook names neither buyer nor number, nor asks` | No buyer term, no number, no `?` | Add segment buyer term or question mark. |
| `hook has no question, number, comparison, or conditional` | Bare statement, no open loop | Add contrast word (vs, before/after, stop, never) or question. |
| `gates failed: {no-duplicate-v1}` | Same hook already built | Reuse existing build or write a new hook. |
| `pixel validation failed: [slide_N]` | Photo background edge spread | Increase blend (0.72+) or check photo isn't too bright. |
| `content_id required` | Empty string passed to resolver | Pass full `AOC:<64hex>` or short `AOC-XXXXXXXX`. |
| `post_url required` | Confirm called without URL | Upload first, then confirm with real URL. |
| `CLOUDFLARE_API_TOKEN missing` | No gen art token | Add to `.env` (see `.env.example`). |
