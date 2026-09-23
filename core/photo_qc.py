"""Photo QC — validate REAL product photos before they enter a packet.

Ported concept from etsysignal/roast/photo_qc.py (magic bytes + presence),
strengthened: sharpness (Laplacian variance), brightness bounds, Etsy
minimum dims (2000px short side). Rendered slides are covered by
core/validate.py; this covers camera photos when product photography lands.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat


def _sharpness(gray: Image.Image) -> float:
    """Variance of Laplacian — higher means sharper. Pillow-only approx."""
    import math
    px = list(gray.getdata())
    w, h = gray.size
    vals = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            c = px[y * w + x]
            lap = (abs(4 * c - px[y * w + x - 1] - px[y * w + x + 1]
                       - px[(y - 1) * w + x] - px[(y + 1) * w + x]))
            vals.append(lap)
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


def check_photo(path: Path | str) -> dict:
    """Check one photo. Returns {ok, issues, width, height, bytes}."""
    path = Path(path)
    issues = []
    if not path.exists():
        return {"ok": False, "issues": ["file_not_found"]}
    size = path.stat().st_size
    if size < 50_000:
        issues.append("suspiciously_small")
    try:
        with Image.open(path) as im:
            im.load()
            w, h = im.size
            if min(w, h) < 2000:
                issues.append(f"below_etsy_minimum:{min(w, h)}px")
            g = im.convert("L")
            if _sharpness(g) < 15:
                issues.append("blurry")
            mean = ImageStat.Stat(g).mean[0]
            if mean < 25:
                issues.append("near_black")
            elif mean > 235:
                issues.append("blown_out")
    except Exception:
        return {"ok": False, "issues": ["unreadable"]}
    return {"ok": not issues, "issues": issues,
            "width": w, "height": h, "bytes": size}


def check_packet_photos(photo_paths: list[Path | str],
                        minimum_ok: int = 3) -> dict:
    """A listing needs real photography across slots. Typographic cards
    don't count — this checks camera photos only."""
    results = [{"file": str(p), **check_photo(p)} for p in photo_paths]
    ok_count = sum(1 for r in results if r["ok"])
    verdict = "PASS" if ok_count >= minimum_ok else "NEEDS_REPLACEMENT"
    return {"verdict": verdict, "photos": len(results),
            "ok_photos": ok_count, "results": results}
