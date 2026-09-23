"""Channel profiles — validated at plan time, applied at publish time.

channels/*.yaml were advisory-only (nothing read them). Now:
- plan() refuses unknown channels (like unknown segments).
- aoc_publish packet carries the channel's hashtags + checklist.
Segment data always wins on conflict (channel is the medium, segment is
the audience).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CHANNELS = ("tiktok", "facebook", "instagram")


def load_channel(channel: str) -> dict:
    """Load a channel profile. Unknown channels raise (no silent default)."""
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel: {channel!r} (known: {list(CHANNELS)})")
    fp = ROOT / "channels" / f"{channel}.yaml"
    return yaml.safe_load(fp.read_text()) if fp.exists() else {"channel": channel}


def channel_hashtags(channel: str, segment_tags: list[str] | None = None) -> list[str]:
    """Segment tags first, channel suggestions after, deduped, order kept.

    Segment data wins on conflict (channel is the medium, segment is the
    audience): a nails creative must lead with #nailtech, not #electrician.
    Found 2026-09-23 — publish packets buried segment tags under 8
    electrician channel tags."""

    prof = load_channel(channel)
    out, seen = [], set()
    for t in list(segment_tags or []) + list(prof.get("suggested_hashtags", []) or []):
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def channel_checklist(channel: str) -> list[str]:
    """Channel-specific publish checklist items."""
    base = {
        "tiktok": [
            "post via Photo Mode (swipeable), not Template auto-play",
            "pick trending sound in-app; never post silent",
        ],
        "facebook": [
            "attach the qualification question to the lead form",
            "target UK trades owners/managers; start Greater Manchester",
        ],
        "instagram": [
            "cross-post winners only; keep grid aesthetic consistent",
        ],
    }
    return base.get(channel, [])
