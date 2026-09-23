"""Image backgrounds — CC photos + Cloudflare Workers AI generated art.

Pinned CC photos live in `assets/photos/` + `sources.json` attribution.
`photo_for()` serves LOCAL files only (no network), so builds are
deterministic and offline when using photos. Missing file → raises
(no silent look-change between runs).

AI generation: `generate()` calls Cloudflare Workers AI flux-1-schnell
(CLOUDFLARE_API_TOKEN + account from .env). Output is saved into
assets/photos + sources.json. Downstream rotation picks it up automatically.
Generations are deterministic for the same prompt+seed via flux-schnell's
step parameter; different prompts produce different creature art.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
import urllib.request

PHOTOS_DIR = Path(__file__).parent.parent / "assets" / "photos"

# Segment → cached photo rotation (deterministic by slide index).
SEGMENT_PHOTOS: dict[str, list[str]] = {
    "electrician": ["electrician-working.jpg", "tool-kit.jpg", "desk-workspace.jpg"],
    "gardeners": ["plants-pots.jpg", "windowsill.jpg"],
    "glimlings": ["puck-gen.jpg", "mosswick-gen.jpg", "plants-pots.jpg", "windowsill.jpg", "desk-workspace.jpg"],
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


def generate(prompt: str, out_name: str, size: str = "1024x1024") -> Path:
    """Cloudflare Workers AI flux-1-schnell → assets/photos/<out_name>.

    Credentials: CLOUDFLARE_API_TOKEN (Workers AI permission) +
    R2_ACCOUNT_ID from .env / environment. Saves the output as-is
    (JPEG bytes from the API) and appends a record to sources.json.
    Returns the cached Path.

    Note: flux-1-schnell ignores size/seed/steps — always returns a
    1024x1024 JPEG. Resize to 1080x1920 happens at render time via
    the same cover-crop pipeline as pinned photos.
    """
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("R2_ACCOUNT_ID", "")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN missing from environment (see .env.example)")
    if not account:
        raise RuntimeError("R2_ACCOUNT_ID missing from environment (see .env.example)")

    body = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read())
    if not data.get("success"):
        raise RuntimeError(f"flux-1-schnell failed: {data.get('errors')}")
    img = base64.b64decode(data["result"]["image"])

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    fp = PHOTOS_DIR / out_name
    fp.write_bytes(img)

    # Append to sources.json
    src = {
        "title": f"Generated: {out_name}",
        "user": "Cloudflare Workers AI",
        "license": "AI-generated",
        "model": "@cf/black-forest-labs/flux-1-schnell",
        "prompt": prompt,
        "cached": str(fp.relative_to(PHOTOS_DIR.parent.parent)),
        "bytes": len(img),
        "timestamp": int(time.time()),
    }
    sources_path = PHOTOS_DIR / "sources.json"
    existing = json.loads(sources_path.read_text()) if sources_path.exists() else []
    existing.append(src)
    sources_path.write_text(json.dumps(existing, indent=1))
    return fp
