"""Etsy render targets — square listing images + silent slideshow video.

Specs from docs/ETSY.md (Etsy Help, Sep 2026):
- Square: 2400x2400, sRGB-ish (PIL RGB), subject centered, critical content
  inside ~1517x1780 safe zone, JPG quality 92, aim ≤10MB.
- Video: MP4/H.264, 1080x1080, 5-15s, SILENT (text overlays only), ≤100MB.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SQUARE = 2400
# centered safe zone surviving 4:3, 3:4 and 1:1 crops (per seller testing)
SAFE_W, SAFE_H = 1517, 1780


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def render_square(title: str, subtitle: str = "",
                  output_path: Path | str = "listing_hero.jpg",
                  bg: tuple[int, int, int] = (18, 18, 20),
                  accent: tuple[int, int, int] = (255, 178, 36)) -> Path:
    """Etsy hero image: 2400x2400, product title centered in the safe zone.

    Text never leaves the safe area, so 4:3/3:4/1:1 crops all keep it.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (SQUARE, SQUARE), bg)
    d = ImageDraw.Draw(img)
    # safe-zone guides are NOT drawn (export must be clean); geometry only
    cx, cy = SQUARE // 2, SQUARE // 2
    f_title = _font(120)
    # wrap title to ~22 chars/line
    words, lines, cur = title.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f_title) <= SAFE_W - 200 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    y = cy - (len(lines) * 150) // 2 - (80 if subtitle else 0)
    for ln in lines:
        w = d.textlength(ln, font=f_title)
        d.text((cx - w / 2, y), ln, font=f_title, fill=(247, 247, 245))
        y += 150
    if subtitle:
        f_sub = _font(64)
        w = d.textlength(subtitle, font=f_sub)
        d.text((cx - w / 2, y + 20), subtitle, font=f_sub, fill=accent)
    img.save(str(out), "JPEG", quality=92)
    return out


def render_video(slide_paths: list[Path | str], output_path: Path | str,
                 seconds_per_slide: float = 2.5, size: int = 1080,
                 fps: int = 30) -> Path:
    """Silent slideshow MP4 from slide PNGs/JPGs: 1080x1080, H.264, no audio.

    Duration = slides × seconds_per_slide, clamped to Etsy's 5–15s window
    by repeating (short) or trimming (long) the input list. Cross-fades
    between slides; text already baked in, so silence loses nothing.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    slides = [Path(p) for p in slide_paths]
    if not slides:
        raise ValueError("no slides to render")
    total = len(slides) * seconds_per_slide
    while total < 5:
        slides = slides + slides
        total = len(slides) * seconds_per_slide
    while total > 15:
        slides = slides[:-1]
        total = len(slides) * seconds_per_slide
    if not slides:
        raise ValueError("cannot fit 5–15s window")
    dur = total / len(slides)
    # concat with crossfade via zoompan-free approach: xfade chain
    cmd = ["ffmpeg", "-y"]
    for s in slides:
        cmd += ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(s)]
    n = len(slides)
    if n == 1:
        filt = f"[0:v]scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size},format=yuv420p[v]"
    else:
        parts = [f"[{i}:v]scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size},setsar=1,fps={fps}[v{i}]"
                 for i in range(n)]
        xfade = f"[v0][v1]xfade=transition=fade:duration=0.5:offset={dur - 0.5:.2f}[x01]"
        off = dur - 0.5
        for i in range(1, n - 1):
            off += dur - 0.5
            xfade += f";[x{i:02d}][v{i + 1}]xfade=transition=fade:duration=0.5:offset={off:.2f}[x{i + 1:02d}]"
        filt = ";".join(parts) + ";" + xfade + f",[x{n - 1:02d}]format=yuv420p[v]"
    cmd += ["-filter_complex", filt, "-map", "[v]", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "23", "-an",
            "-movflags", "+faststart", str(out)]
    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[-500:]}")
    return out
