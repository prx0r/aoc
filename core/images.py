"""Image backgrounds — cached CC photos today, generated art tomorrow.

Today: six Wikimedia Commons photos pinned in `assets/photos/` with full
attribution in `assets/photos/sources.json`. `photo_for()` serves LOCAL
files only — it never touches the network, so builds stay deterministic
and offline. Missing file → raises (never silently fall back in a way
that changes a deck's look between runs; the caller decides fallback).

Attribution: CC0 / public-domain need none (credited anyway in
sources.json). CC BY 2.0 photos (AaronY, Shixart1985) REQUIRE credit —
`credit_line()` feeds the publish packet caption; keep it there.

Tomorrow (handoff): `generate()` is the seam for Cloudflare Workers AI
image models (`@cf/black-forest-labs/flux-1-schnell`). Blocked 2026-09-23:
the `CLOUDFLARE_API_TOKEN` in env 401s even on token-verify — it needs a
token with Workers AI permission on the account in `.env` (R2_ACCOUNT_ID).
When that exists: implement `generate()` to download into `assets/photos/`
+ append sources.json, then everything downstream works unchanged.
"""

from __future__ import annotations

from pathlib import Path

PHOTOS_DIR = Path(__file__).parent.parent / "assets" / "photos"

# Segment → cached photo rotation (deterministic by slide index).
# Curated 2026-09-23: "Bound to be an Electrician p113" dropped from rotation
# (vintage engraving — right theme, wrong century; file stays cached).
SEGMENT_PHOTOS: dict[str, list[str]] = {
    "electrician": ["electrician-working.jpg", "tool-kit.jpg", "desk-workspace.jpg"],
    "gardeners": ["plants-pots.jpg", "windowsill.jpg"],
    "glimlings": ["plants-pots.jpg", "windowsill.jpg", "desk-workspace.jpg"],
}

# CC BY files (credit required when used).
NEEDS_CREDIT = {"electrician-working.jpg": "Aaron Y",
                "desk-workspace.jpg": "Shixart1985"}


def photo_for(segment: str, index: int) -> Path | None:
    """Local cached photo for (segment, slide). None = no mapping (gradient).

    Raises FileNotFoundError if the mapping points at a missing file —
    a deck must never silently change looks between runs.
    """
    files = SEGMENT_PHOTOS.get(segment or "")
    if not files:
        return None
    fp = PHOTOS_DIR / files[index % len(files)]
    if not fp.exists():
        raise FileNotFoundError(f"pinned photo missing: {fp}")
    return fp


def credit_line(segment: str, count: int) -> str:
    """Attribution for CC BY photos a deck may show. Empty if none needed."""
    files = SEGMENT_PHOTOS.get(segment or "")
    if not files:
        return ""
    used = {files[i % len(files)] for i in range(count)}
    names = sorted({NEEDS_CREDIT[f] for f in used if f in NEEDS_CREDIT})
    if not names:
        return ""
    return "Photos: " + ", ".join(names) + " via Wikimedia Commons (CC BY 2.0)."


def generate(prompt: str, out_name: str) -> Path:
    """FUTURE seam: Cloudflare Workers AI text-to-image → assets/photos/.

    Blocked: needs a live CLOUDFLARE_API_TOKEN with Workers AI permission
    (current token 401s). When available, implement: POST
    /accounts/{id}/ai/run/@cf/black-forest-labs/flux-1-schnell, save bytes
    to assets/photos/<out_name>, append sources.json with model + prompt.
    """
    raise NotImplementedError(
        "generate() needs a live CLOUDFLARE_API_TOKEN with Workers AI "
        "permission (current token 401s on verify). See module docstring.")
