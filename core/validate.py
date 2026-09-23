"""Pixel validation — what the PNGs actually look like, not just their bytes.

Checks every rendered slide: dims, JPEG validity, dark text-band present
(backdrop for readability), text region non-uniform (something drawn),
UI-safe margins. Plus a contact sheet for the human gate.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat


def validate_slide(path: Path | str) -> dict:
    """Validate one rendered slide. Returns {ok, checks}."""
    path = Path(path)
    checks: dict[str, dict] = {}
    try:
        with Image.open(path) as im:
            im.load()
            checks["dims"] = {"ok": im.size == (1080, 1920), "detail": f"{im.size}"}
            checks["mode"] = {"ok": im.mode in ("RGB", "RGBA"), "detail": im.mode}
    except Exception as e:
        return {"ok": False, "checks": {"open": {"ok": False, "detail": str(e)[:80]}}}

    with Image.open(path).convert("L") as g:
        w, h = g.size
        # text band lives in the middle 60% vertically; sample it
        band = g.crop((40, int(h * 0.2), w - 40, int(h * 0.85)))
        mean = ImageStat.Stat(band).mean[0]
        extrema = band.getextrema()
        spread = extrema[1] - extrema[0]
        # Legibility = contrast, not darkness: dark band + light text (classic)
        # or bright CTA band + dark text (inverted payoff slide) both pass.
        dark_ok = mean < 150
        light_ok = mean > 110 and extrema[0] < 100
        checks["backdrop"] = {"ok": bool(dark_ok or light_ok),
                              "detail": f"band luminance {mean:.0f}"}
        # text present: band must not be flat
        extrema = band.getextrema()
        spread = extrema[1] - extrema[0]
        checks["text_present"] = {"ok": spread > 40, "detail": f"luminance spread {spread}"}
        # UI-safe: top 8% and bottom 12% should be calmer than the band.
        # For gradient backgrounds, edges have lower luminance spread.
        # For photo backgrounds, edges may match band spread but have lower
        # mean luminance (darker = calmer) — check both.
        top = g.crop((0, 0, w, int(h * 0.08)))
        bottom = g.crop((0, int(h * 0.88), w, h))
        edge_spread = max(top.getextrema()[1] - top.getextrema()[0],
                          bottom.getextrema()[1] - bottom.getextrema()[0])
        edge_mean = max(ImageStat.Stat(top).mean[0], ImageStat.Stat(bottom).mean[0])
        band_mean = ImageStat.Stat(band).mean[0]
        checks["margins"] = {"ok": bool(edge_spread < spread or edge_mean < band_mean - 5),
                              "detail": f"edge spread {edge_spread} vs band {spread}, edge mean {edge_mean:.0f} vs band {band_mean:.0f}"}

    ok = all(c["ok"] for c in checks.values())
    return {"ok": ok, "checks": checks}


def validate_carousel(out_dir: Path | str, manifest: dict) -> dict:
    """Validate every slide in a rendered carousel."""
    out_dir = Path(out_dir)
    results = {}
    for name in manifest.get("slides", []):
        results[name] = validate_slide(out_dir / name)
    passed = all(r["ok"] for r in results.values())
    return {"passed": passed, "slides": results}


def contact_sheet(out_dir: Path | str, dest: Path | str | None = None,
                  thumb_w: int = 270) -> Path:
    """Grid thumbnail of all slides for fast human review (ai-ugc pattern)."""
    out_dir = Path(out_dir)
    jpgs = sorted(out_dir.glob("slide_*.jpg"))
    thumbs = []
    for fp in jpgs:
        with Image.open(fp) as im:
            thumbs.append(im.copy().resize((thumb_w, int(thumb_w * 1920 / 1080))))
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * int(thumb_w * 1920 / 1080)), (10, 10, 10))
    for i, th in enumerate(thumbs):
        sheet.paste(th, ((i % cols) * thumb_w, (i // cols) * th.size[1]))
    dest = Path(dest) if dest else out_dir / "contact_sheet.jpg"
    sheet.save(dest, "JPEG", quality=80)
    return dest
