"""Slide renderer — PIL-based 1080x1920 image compositor.

Stolen from ClipFactory's render_slide(). Handles:
- Cover-crop to 9:16
- Text wrapping with auto-shrink
- Semi-transparent backdrop for readability
- White text with black stroke
- JPEG output at quality 92
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


def render_slide(
    text: str,
    background: Image.Image | Path | str,
    output_path: Path | str,
    font_size: int = 72,
    font_path: str | None = None,
    text_position: float = 0.7,
    dark_overlay_opacity: int = 160,
    quality: int = 92,
) -> Path:
    """Render a single slide as 1080x1920 JPEG.

    Args:
        text: The slide text (10 words max for hooks, 15 for body).
        background: Source image (PIL Image, Path, or URL string).
        output_path: Where to save the rendered JPEG.
        font_size: Starting font size (auto-shrinks to fit).
        font_path: Path to .ttf font file. None = default.
        text_position: Vertical position (0=top, 1=bottom). 0.7 = lower third.
        dark_overlay_opacity: Opacity of the dark band behind text (0-255).
        quality: JPEG quality (1-95).

    Returns:
        Path to the rendered JPEG.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load and cover-crop background to 1080x1920
    if isinstance(background, (str, Path)):
        bg = Image.open(background)
    else:
        bg = background.copy()

    bg = ImageOps.fit(bg, (1080, 1920), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))

    # Create dark overlay for text readability
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Measure text height to size the backdrop
    font = _get_font(font_size, font_path)
    wrapped = _wrap_text(text, font, int(1080 * 0.84))
    bbox = draw_overlay.multiline_textbbox((0, 0), wrapped, font=font, spacing=12)
    text_h = bbox[3] - bbox[1]
    text_w = bbox[2] - bbox[0]

    # Position the dark band
    band_y = int(1920 * text_position - text_h / 2)
    band_padding = 40
    band_top = max(0, band_y - band_padding)
    band_bottom = min(1920, band_y + text_h + band_padding)

    # Draw semi-transparent rounded rectangle
    draw_overlay.rounded_rectangle(
        [(40, band_top), (1040, band_bottom)],
        radius=20,
        fill=(0, 0, 0, dark_overlay_opacity),
    )

    # Composite overlay onto background
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, overlay)

    # Draw text
    draw = ImageDraw.Draw(bg)
    text_x = (1080 - text_w) // 2
    text_y = band_y

    # Black stroke for legibility
    for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.multiline_text((text_x + dx, text_y + dy), wrapped, font=font, fill=(0, 0, 0), spacing=12, align="center")

    # White text
    draw.multiline_text((text_x, text_y), wrapped, font=font, fill=(255, 255, 255), spacing=12, align="center")

    # Save as JPEG
    bg = bg.convert("RGB")
    bg.save(str(output_path), "JPEG", quality=quality)

    return output_path


def render_slideshow(
    script: list[dict],
    output_dir: Path | str,
    backgrounds: list[Image.Image | Path | str] | None = None,
    font_path: str | None = None,
) -> list[Path]:
    """Render a full slideshow from a script.

    Args:
        script: List of {"text": str, "position": float} dicts.
        output_dir: Directory to save rendered slides.
        backgrounds: Source images (one per slide, or None for solid colors).
        font_path: Path to .ttf font file.

    Returns:
        List of paths to rendered slides.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i, slide in enumerate(script):
        text = slide.get("text", "")
        position = slide.get("position", 0.7)

        # Use provided background or generate solid color
        if backgrounds and i < len(backgrounds):
            bg = backgrounds[i]
        else:
            bg = _solid_background(1080, 1920, _color_for_index(i))

        path = render_slide(
            text=text,
            background=bg,
            output_path=output_dir / f"slide_{i:02d}.jpg",
            font_path=font_path,
            text_position=position,
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

def _get_font(size: int, path: str | None = None) -> ImageFont.FreeTypeFont:
    """Load font, falling back to default."""
    if path:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    # Try common system fonts
    for name in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                 "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Wrap text to fit within max_width, auto-shrinking if needed."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current_line = []
        for word in words:
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


def _solid_background(w: int, h: int, color: tuple) -> Image.Image:
    """Create a solid color background."""
    return Image.new("RGB", (w, h), color)


def _color_for_index(i: int) -> tuple:
    """Generate distinct background colors for slides without images."""
    colors = [
        (15, 15, 15),      # near-black
        (20, 30, 48),      # dark blue
        (48, 25, 52),      # dark purple
        (25, 48, 20),      # dark green
        (48, 35, 15),      # dark brown
        (15, 35, 48),      # teal
        (48, 15, 25),      # dark red
        (30, 30, 30),      # dark gray
    ]
    return colors[i % len(colors)]
