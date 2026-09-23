"""Gradient backgrounds — 382 curated gradients from uiGradients (MIT).

Replaces the hardcoded gradient palette with community-curated gradients
that render beautifully at 1080×1920 with white or dark text overlays.

Source: https://github.com/ghosh/uiGradients (6000 stars, MIT license)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

GRADIENTS_PATH = Path(__file__).parent.parent.parent / "uiGradients" / "gradients.json"
_CACHE: list[dict] | None = None


def _load() -> list[dict]:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(GRADIENTS_PATH.read_text())
    return _CACHE


def gradients_for_segment(segment: str, count: int = 6) -> list[dict]:
    """Pick gradients matching a segment's accent color family.
    
    Deterministic: same segment always gets same gradients.
    Returns list of {name, colors, text_color} dicts.
    """
    all_g = _load()
    # Map segments to color families
    FAMILY = {
        "electrician": "blue", "cleaners": "green", "gardeners": "green",
        "glimlings": "gold", "nails": "pink", "lashes": "pink",
        "hair": "purple", "plumber": "blue", "sole_trader": "dark",
        "car_detailers": "dark", "driving_instructors": "blue",
        "weddings": "pink", "beautician": "pink",
        "dog_groomers": "warm", "powthings": "warm",
        "garden_familiars": "green",
    }
    family = FAMILY.get(segment, "dark")
    
    # Filter by color family keywords
    FAMILY_KEYWORDS = {
        "blue": ["blue", "sky", "ocean", "sea", "ice", "deep", "royal"],
        "green": ["green", "grass", "mint", "forest", "nature", "spring"],
        "gold": ["gold", "orange", "amber", "fire", "sun", "warm"],
        "pink": ["pink", "purple", "rose", "berry", "violet", "orchid"],
        "warm": ["warm", "sunset", "amber", "fire", "orange", "red"],
        "dark": ["dark", "night", "midnight", "black", "deep", "royal"],
    }
    keywords = FAMILY_KEYWORDS.get(family, FAMILY_KEYWORDS["dark"])
    
    # Score gradients by keyword match
    scored = []
    for g in all_g:
        name_lower = g["name"].lower()
        score = sum(1 for kw in keywords if kw in name_lower)
        # Prefer dark backgrounds (better for white text)
        avg_brightness = sum(int(c[1:3], 16) for c in g["colors"]) / len(g["colors"])
        if avg_brightness < 120:
            score += 1
        scored.append((score, g))
    
    # Sort by score, take top N, shuffle deterministically
    scored.sort(key=lambda x: -x[0])
    selected = [g for _, g in scored[:count * 2]]
    # Deterministic shuffle based on segment name
    rng = random.Random(segment)
    rng.shuffle(selected)
    return selected[:count]


def render_gradient(colors: list[str], width: int = 1080, height: int = 1920) -> Image.Image:
    """Render a vertical gradient from hex colors to a PIL Image."""
    from PIL import Image, ImageDraw
    
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    
    rgb_colors = [tuple(int(c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for c in colors]
    
    for y in range(height):
        t = y / height
        idx = int(t * (len(rgb_colors) - 1))
        idx = min(idx, len(rgb_colors) - 2)
        local_t = (t * (len(rgb_colors) - 1)) - idx
        c1, c2 = rgb_colors[idx], rgb_colors[idx + 1]
        r = int(c1[0] + (c2[0] - c1[0]) * local_t)
        g = int(c1[1] + (c2[1] - c1[1]) * local_t)
        b = int(c1[2] + (c2[2] - c1[2]) * local_t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


def text_color_for_gradient(colors: list[str]) -> str:
    """Return 'white' or 'black' based on gradient brightness."""
    avg = sum(int(c[1:3], 16) for c in colors) / len(colors)
    return "white" if avg < 128 else "black"
