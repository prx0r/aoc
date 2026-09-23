# MINING — what we stole and from where

Clones live in `/root/reference/` (not duplicated here — disk is 89% full).
AOC re-implements the minimal pattern in Python, no new infra.

## /root/content (local repo) — receipt chain + gates
- `core/receipt.py` ← hash-chained `content.jsonl`, verify function.
- `core/state.py` ← every path to published passes `in_review`.
- Lesson: model phrases, never discovers the fact. Kept: proofs.yaml requirement.

## feyzilim/clipfactory — slide renderer + photo-mode workflow
- `render/slide.py` ← `render_slide()` port: cover-crop 1080×1920, wrap + auto-shrink,
  dark band, white+stroke text, JPEG q92, ZIP export.
- `core/carousel.py` ← 3-stage versioned pipeline (generate → select → render).
- Lesson: slideshows are **native image posts, not MP4s**. Add trending audio in-app.

## Tytandoteth/content-management-dashboard — approval as structure
- `core/state.py` ← `TRANSITIONS` graph + `checkTransition()` + BFS invariant.
- Lesson: no-publish-tool by design. AI prepares, human approves. Stub/deterministic
  path must exercise the full pipeline with £0 spend.

## kendrekaran/ai-ugc-slideshows — JSON contracts + idempotency
- `core/carousel.py` ← `script.json` → `manifest.json` (sha256) → ZIP; refuse corrupt.
- Lesson: notification-as-overlay (keep dynamic text in JSON, render programmatically),
  dry-run-first (`--send` only touches network), receipt fingerprints.

## clawvisual — agent-compatible service shape
- `mcp_server.py` ← tools/list + tools/call stdio shape, now 19 tools (was 5 at mining time).
- Lesson: MCP-compatible = powops/agents can query without new infra.

## steadyfetch/n8n-templates — feedback side only
- `core/memory.py` ← audience×hook×… → leads/sales ranking; mutate winners by leads.
- Lesson: scrape ad transcripts/hooks/CTAs → Sheets; feed competitor intelligence back
  into hook bank. NOT building n8n — Python/MCP is cleaner here.
