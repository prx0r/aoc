# AGENTS.md — aoc

## What this repo is
TikTok slideshow factory for AI Onboard. Deterministic pipeline with
fail-closed gates, human review, and a measured learning loop. Read
`docs/HOW_IT_WORKS.md` before touching anything. Current state:
16 segments · 20 MCP tools · 90 tests green · docs/AUDIT.md (latest audit) ·
THREADS.md (open work).

## How to work here
1. Segments are skins: copy never crosses trades. New segment = copy
   `segments/electrician/`'s 4 YAMLs, rewrite copy, run tests.
2. Claims come from `claims.yaml` only. Never invent stats; never fuzzy-match
   numbers. Unknown stat claims raise — that's correct behavior.
3. Offer copy comes from `offers.yaml` only. If aionboard OFFER.md changed,
   re-snapshot (bump version) and let the revalidation gate do its job.
4. Gates run before render. If a build refuses, fix the DATA (skin/hook),
   not the gate. Weakening a gate needs a written reason in the commit.
5. Bank hygiene is tested: every hook in every bank must pass gates.
   `python3 -m pytest tests/ -q` must stay green.
6. Receipts are append-only. Never edit `receipts/`, never force-push history.
7. Secrets live in `.env` (gitignored). Verify with `git status` before every
   commit that no secret, ZIP, JPG, PNG, or DB file is staged.
8. Manual posting only. There is no auto-post tool and there must never be one.

## Commands
- `python3 -m pytest tests/ -q` — full suite (90 tests, no network)
- `python3 mcp_server.py aoc_validate '{"hook":"...","segment":"nails"}'` — cheap check
- `python3 -m web.viewer` — gallery at :8798
- `AOC_DB=/tmp/x.db python3 -m pytest tests/ -q` — isolated store (conftest does this per-test anyway)

## Where things stand
- `THREADS.md` — open work (T1 first post+measurement unblocks the learning loop).
- `docs/AUDIT.md` — appenditive repo audits, newest first.
- Upstream sync: `offers.yaml` pins aionboard OFFER.md commit; `segments/glimlings/`
  mirrors powrobots brand-identity names. Verify with the ancestor check in AUDIT.md
  before touching either.

## Do not
- Add segments/templates without updating `SEGMENT_IDS`-dependent docs (`docs/SEGMENTS.md`, `docs/VERTICALS.md`, mcp template lists).
- Change ID inputs without bumping `RENDER_V` or documenting the migration.
- Quote prices anywhere except via the offer registry + segment close.
- Treat `aoc_<12hex>` legacy IDs as resolvable — use `core/legacy.py`.
