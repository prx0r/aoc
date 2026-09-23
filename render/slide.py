"""Slide renderer — PIL-based 1080x1920 compositor, premium pass (2026-09-23).

Patterns stolen from: tiktok-carousel-generator (TikTok-native heavy type),
instagram-carousel-mcp (themes, scrims, brand bug), carousel-english skill
(safe zones, no bottom-20% text), easy-pil (gradient fills), postcanvas
(shrink-to-fit, watermark).

Design system (deterministic — no network, no randomness without seed):
- Vertical gradient backgrounds anchored to a per-segment accent color.
- Montserrat ExtraBold (vendored variable font), auto-shrink-to-fit.
- Ghost slide numeral behind the text, accent rule above it.
- Progress dots + brand wordmark kept subtle for the UI-safe margins check.
- CTA (kind == "close") slides invert: accent background, dark text.
- Safe zone: main text lives y 200-1620 (top 8% / bottom 12% stay calm).
"""

from __future__ import annotations

import hashlib
import random
import textwrap  # noqa: F401  (kept for backward-compat imports)
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
SAFE_TOP, SAFE_BOTTOM = 200, 1620
MARGIN_TOP, MARGIN_BOTTOM = int(H * 0.08), int(H * 0.88)
FONTS_DIR = Path(__file__).parent / "fonts"

# Per-deck accents (segment hash picks one — stable per trade, distinct across).
ACCENTS = [
    (255, 210, 63),    # gold
    (255, 107, 107),   # coral
    (78, 205, 196),    # mint
    (78, 168, 222),    # sky
    (179, 136, 235),   # lilac
    (255, 159, 67),    # amber
]

_FONT_CACHE: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}


def render_slide(
    text: str,
    background: Image.Image | Path | str | None = None,
    output_path: Path | str = "",
    font_size: int = 88,
    font_path: str | None = None,
    text_position: float = 0.6,
    dark_overlay_opacity: int = 160,
    quality: int = 92,
    kind: str = "body",
    accent: tuple[int, int, int] = ACCENTS[0],
    slide_index: int = 0,
    slide_total: int = 1,
    brand: str = "AI ONBOARD",
) -> Path:
    """Render a single slide as 1080x1920 JPEG.

    Args:
        text: Slide text (auto-shrink-to-fit; hooks render huge).
        background: Source photo (PIL/Path/URL string), or None for a
            generated gradient in the deck accent family.
        output_path: Where to save the rendered JPEG.
        font_size: Starting size (shrinks to fit the safe zone).
        font_path: Custom .ttf (overrides Montserrat).
        text_position: Accepted for backward compat; composition is now
            centered in the safe zone (position no longer moves text).
        dark_overlay_opacity: Accepted for backward compat (scrim is baked
            into the gradient/photo treatment now).
        quality: JPEG quality (1-95).
        kind: "hook" (huge) | "body" | "close" (inverted CTA payoff).
        accent: RGB deck accent.
        slide_index / slide_total: 0-based position (ghost numeral + dots).
        brand: Wordmark top-center (empty string disables).

    Returns:
        Path to the rendered JPEG.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    is_cta = kind == "close"

    base = _background(background, accent, slide_index if background is None else -1, is_cta)
    img = base.convert("RGBA")

    draw = ImageDraw.Draw(img)
    ink = (17, 17, 17) if is_cta else (255, 255, 255)

    # Fit type: start big, shrink until the block fits the safe zone.
    start = font_size if font_size != 88 else {"hook": 108, "close": 96}.get(kind, 88)
    max_w, max_h = 900, 1150 if kind == "hook" else 1250
    size = start
    font = _get_font(size, font_path, 800)
    wrapped = _wrap_text(text, font, max_w)
    while size > 44:
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=int(size * 0.16))
        if bbox[2] - bbox[0] <= max_w and bbox[3] - bbox[1] <= max_h:
            break
        size -= 4
        font = _get_font(size, font_path, 800)
        wrapped = _wrap_text(text, font, max_w)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=int(size * 0.16))
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = (W - tw) // 2
    cy = (SAFE_TOP + SAFE_BOTTOM - th) // 2

    # Ghost numeral behind text, centered on the text block (editorial depth).
    _ghost_numeral(img, slide_index + 1, accent if not is_cta else (0, 0, 0),
                   cy + th // 2)

    # Accent rule above the text.
    rule_w, rule_h = 120, 10
    rule = Image.new("RGBA", (rule_w, rule_h), (0, 0, 0, 0))
    ImageDraw.Draw(rule).rounded_rectangle(
        [(0, 0), (rule_w, rule_h)], radius=rule_h // 2,
        fill=ink if is_cta else accent + (255,))
    img.alpha_composite(rule, ((W - rule_w) // 2, cy - 56))

    # Soft drop shadow (blurred dark copy), then stroked main text.
    if not is_cta:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text(
            (cx, cy + 7), wrapped, font=font, fill=(0, 0, 0, 170),
            spacing=int(size * 0.16), align="center")
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        img = Image.alpha_composite(img, sh)
        draw = ImageDraw.Draw(img)
        sw = max(2, size // 30)
        draw.multiline_text((cx, cy), wrapped, font=font, fill=ink,
                            spacing=int(size * 0.16), align="center",
                            stroke_width=sw, stroke_fill=(0, 0, 0))
    else:
        draw.multiline_text((cx, cy), wrapped, font=font, fill=ink,
                            spacing=int(size * 0.16), align="center")

    if brand and not is_cta:
        # CTA payoff slides stay clean: the brand was established on every
        # prior slide, and any mark in the margins trips the UI-safe check
        # on bright backgrounds.
        _wordmark(img, brand, dark=is_cta)
    _progress(img, slide_index, slide_total, accent if not is_cta else (17, 17, 17))

    rgb = img.convert("RGB")
    rgb.save(str(output_path), "JPEG", quality=quality)
    return output_path


def render_slideshow(
    script: list[dict],
    output_dir: Path | str,
    backgrounds: list[Image.Image | Path | str] | None = None,
    font_path: str | None = None,
    segment: str = "electrician",
    brand: str = "AI ONBOARD",
) -> list[Path]:
    """Render a full slideshow from a script.

    Args:
        script: List of {"text": str, "position": float, "kind": str} dicts.
        output_dir: Directory to save rendered slides.
        backgrounds: Source photos (one per slide, or None for gradients).
        font_path: Path to .ttf font file.
        segment: Picks the deck accent deterministically.
        brand: Wordmark on every slide (empty disables).

    Returns:
        List of paths to rendered slides.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    accent = _accent_for(segment)
    total = len(script)

    paths = []
    for i, slide in enumerate(script):
        bg = backgrounds[i] if backgrounds and i < len(backgrounds) else None
        path = render_slide(
            text=slide.get("text", ""),
            background=bg,
            output_path=output_dir / f"slide_{i:02d}.jpg",
            font_path=font_path,
            kind=slide.get("kind", "body"),
            accent=accent,
            slide_index=i,
            slide_total=total,
            brand=brand,
        )
        paths.append(path)
    return paths


def export_zip(slide_paths: list[Path], zip_path: Path | str) -> Path:
    """Export rendered slides as a ZIP for TikTok upload."""
    import zipfile

    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in slide_paths:
            zf.write(path, path.name)

    return zip_path


# ── Internal helpers ──────────────────────────────────────────

def _accent_for(segment: str) -> tuple[int, int, int]:
    """Stable per-segment deck accent."""
    h = int(hashlib.sha256(segment.encode()).hexdigest(), 16)
    return ACCENTS[h % len(ACCENTS)]


def _get_font(size: int, path: str | None = None, weight: int = 800):
    """Montserrat (vendored VF) at size+weight, else system fallback."""
    key = (size, weight, path or "")
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if path:
        try:
            f = ImageFont.truetype(path, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            pass
    vf = FONTS_DIR / "Montserrat-VF.ttf"
    if vf.exists():
        try:
            f = ImageFont.truetype(str(vf), size)
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            pass
    for name in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                 "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]:
        try:
            f = ImageFont.truetype(name, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Wrap text to fit within max_width, auto-shrinking if needed.

    Long slash/hyphen tokens (Instagram/TikTok/WhatsApp) are split first —
    an unwrappable token bleeds past its backdrop (caught in human review).
    """
    import re
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        # pre-split tokens that can never fit on one line
        split_words: list[str] = []
        for word in words:
            bbox = font.getbbox(word)
            if bbox[2] - bbox[0] > max_width and re.search(r"[/\-–—]", word):
                split_words.extend(re.split(r"(?<=[/\-–—])", word))
            else:
                split_words.append(word)
        current_line = []
        for word in split_words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
    return "\n".join(lines)


def _fast_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    """Vertical gradient via a 1px-wide strip scaled up (fast)."""
    strip = Image.new("RGB", (1, h))
    spx = strip.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        spx[0, y] = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def _background(bg, accent: tuple, slide_index: int, is_cta: bool) -> Image.Image:
    """Deck background: photo+scrim, or accent-anchored gradient + glow + grain."""
    if isinstance(bg, (str, Path)):
        photo = Image.open(bg)
        photo = ImageOps.fit(photo, (W, H), method=Image.Resampling.LANCZOS,
                             centering=(0.5, 0.45)).convert("RGB")
        dark = Image.new("RGB", (W, H), (5, 6, 12))
        return Image.blend(photo, dark, 0.55)
    if is_cta:
        light = tuple(min(255, c + 40) for c in accent)
        deep = tuple(max(0, c - 90) for c in accent)
        img = _fast_gradient(W, H, light, deep)
    else:
        # Near-black gradient tilted toward the accent hue.
        tint = tuple(c // 7 for c in accent)
        top = (13 + tint[0], 16 + tint[1], 26 + tint[2])
        img = _fast_gradient(W, H, top, (6, 8, 14))
        # Soft radial glow behind the text zone.
        glow = Image.new("RGB", (W, H), (0, 0, 0))
        ImageDraw.Draw(glow).ellipse(
            [(W // 2 - 480, 560), (W // 2 + 480, 1400)],
            fill=tuple(min(255, c // 3 + 18) for c in accent))
        glow = glow.filter(ImageFilter.GaussianBlur(180))
        img = Image.blend(img, glow, 0.28)
    # Film grain (seeded Random → byte-identical across runs).
    rnd = random.Random(777 + (slide_index if slide_index >= 0 else 0))
    grain = Image.frombytes("L", (W, H), rnd.randbytes(W * H))
    lum = grain.point(lambda v: 10 if v > 140 else 0)
    img = Image.composite(Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.06),
                          img, lum)
    return img


def _ghost_numeral(img: Image.Image, n: int, color: tuple, center_y: int) -> None:
    """Huge translucent slide number behind the text."""
    size = 460
    font = _get_font(size, None, 800)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    txt = f"{n:02d}"
    bbox = d.textbbox((0, 0), txt, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((W - tw) // 2, center_y - th // 2), txt, font=font,
           fill=color + (30,), stroke_width=2, stroke_fill=color + (46,))
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(layer)


def _wordmark(img: Image.Image, brand: str, dark: bool = False) -> None:
    """Small letterspaced brand mark, top-center (kept dim for margins check)."""
    font = _get_font(30, None, 600)
    spaced = "  ".join(brand.upper())
    d = ImageDraw.Draw(img)
    bbox = d.textbbox((0, 0), spaced, font=font)
    tw = bbox[2] - bbox[0]
    fill = (17, 17, 17, 150) if dark else (255, 255, 255, 110)
    d.text(((W - tw) // 2, 92), spaced, font=font, fill=fill)


def _progress(img: Image.Image, index: int, total: int, active: tuple) -> None:
    """Subtle progress dots above the bottom safe line."""
    if total < 2:
        return
    d = ImageDraw.Draw(img)
    r, gap = 8, 26
    width = total * (2 * r) + (total - 1) * gap
    x0 = (W - width) // 2
    y = 1640
    for i in range(total):
        x = x0 + i * (2 * r + gap)
        if i == index:
            d.ellipse([(x, y - r), (x + 2 * r, y + r)], fill=active + (230,))
        elif i < index:
            d.ellipse([(x, y - r), (x + 2 * r, y + r)], fill=(255, 255, 255, 90))
        else:
            d.ellipse([(x, y - r), (x + 2 * r, y + r)], fill=(255, 255, 255, 45))
