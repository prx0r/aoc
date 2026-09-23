"""Image backgrounds — CC photos + Cloudflare Workers AI generated art.

Pinned CC photos live in `assets/photos/` + `sources.json` attribution.
`photo_for()` serves LOCAL files only (no network), so builds are
deterministic and offline when using photos. Missing file → raises
(no silent look-change between runs).

AI generation: `generate()` calls Cloudflare Workers AI image models.
Primary: `@cf/bytedance/stable-diffusion-xl-lightning` (cheapest, fast,
1024×1024 PNG output). Fallback: `@cf/black-forest-labs/flux-1-schnell`
(faster, JPEG output). Output saved into assets/photos + sources.json.
Downstream rotation picks it up automatically.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
import urllib.request

PHOTOS_DIR = Path(__file__).parent.parent / "assets" / "photos"

# Image gen models in priority order (cheapest first).
IMAGE_MODELS = [
    ("@cf/bytedance/stable-diffusion-xl-lightning", "lightning"),
    ("@cf/black-forest-labs/flux-1-schnell", "schnell"),
]

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


def generate(prompt: str, out_name: str) -> Path:
    """Cloudflare Workers AI text-to-image → assets/photos/<out_name>.

    Tries IMAGE_MODELS in order (lightning first — cheapest/fastest).
    Lightning returns raw PNG; schnell returns JSON with base64 image.
    Saves as-is, appends a record to sources.json. Returns the cached Path.

    Credentials: CLOUDFLARE_API_TOKEN + R2_ACCOUNT_ID from .env / environment.
    """
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("R2_ACCOUNT_ID", "")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN missing from environment (see .env.example)")
    if not account:
        raise RuntimeError("R2_ACCOUNT_ID missing from environment (see .env.example)")

    body = json.dumps({"prompt": prompt}).encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    last_err = None

    for model, label in IMAGE_MODELS:
        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}",
                data=body, headers=headers)
            resp = urllib.request.urlopen(req, timeout=180)
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "json" in ct:
                data = json.loads(raw)
                if not data.get("success"):
                    last_err = f"{model}: {data.get('errors')}"
                    continue
                img = base64.b64decode(data["result"]["image"])
            else:
                img = raw
            dt = time.time() - t0
            break
        except Exception as e:
            last_err = f"{model}: {e}"
            continue
    else:
        raise RuntimeError(f"all image models failed: {last_err}")

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    fp = PHOTOS_DIR / out_name
    fp.write_bytes(img)

    sources_path = PHOTOS_DIR / "sources.json"
    existing = json.loads(sources_path.read_text()) if sources_path.exists() else []
    existing.append({
        "title": f"Generated: {out_name}",
        "user": "Cloudflare Workers AI",
        "license": "AI-generated",
        "model": model,
        "prompt": prompt,
        "cached": f"assets/photos/{out_name}",
        "bytes": len(img),
        "time_s": round(dt, 1),
        "timestamp": int(time.time()),
    })
    sources_path.write_text(json.dumps(existing, indent=1))
    return fp
