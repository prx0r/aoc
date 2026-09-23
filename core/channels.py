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


def channel_sound(channel: str, template: str) -> str:
    """Trending sound recommendation per format. Music is REQUIRED for
    TikTok carousel ads. Mismatched energy kills distribution."""
    prof = load_channel(channel)
    sounds = prof.get("sound_by_format", {})
    return sounds.get(template, "lo-fi beat — safe default, match energy to content")


def channel_caption(channel: str, hook: str, segment: str, close: str) -> str:
    """200+ character SEO caption for TikTok search indexing.

    Structure: hook restatement + value promise + comment prompt + close.
    TikTok indexes captions heavily for search — keywords matter.
    """
    # Segment-specific value lines (what the viewer gets)
    value_lines = {
        "electrician": "AI triages your enquiries, drafts quotes while you're on the tools, and follows up automatically. You approve every send. No subscription, no lock-in.",
        "cleaners": "AI handles your scheduling, chases payments, and wins back paused plans while you clean. You approve every message. Setup takes about an hour.",
        "gardeners": "AI records your rounds, chases debt, and wins back lapsed streets while you work. You approve every send. No contract, cancel anytime.",
        "glimlings": "Tiny magical creatures that bring your plants, desk, and bedroom to life. Name it, choose its colours, scan to connect. Each one has a personality and a purpose.",
        "nails": "AI triages your DMs, takes deposits, and sends fill reminders while you do sets. You approve every message. No subscription.",
        "lashes": "AI manages your fill intervals, sends consent reminders, and takes deposits while you work. You approve everything. Setup takes about an hour.",
        "hair": "AI triages your enquiries by travel zone, takes bookings, and sends colour refresh reminders. You approve every message.",
    }
    comment_prompts = {
        "electrician": "Which would you automate first — quotes or follow-ups?",
        "cleaners": "What takes more time — the cleaning or the chasing?",
        "gardeners": "How many skips went unlogged this month?",
        "glimlings": "Which Glimling would you name first — and where would it live?",
        "nails": "How many sets walked away without a deposit this week?",
        "lashes": "How many fills slipped because nobody sent a reminder?",
        "hair": "How many out-of-area enquiries wasted your time this week?",
    }
    val = value_lines.get(segment, "AI handles your admin while you do the work. You approve everything. Setup takes about an hour.")
    cp = comment_prompts.get(segment, "What would you automate first?")
    hashtags = " ".join([
        f"#{segment}", "#smallbusiness", "#ukbusiness", "#ai",
        "#automation", "#aiagent", "#workflow", "#timemanagement",
    ])
    # Build caption: hook + value + comment prompt + close + hashtags
    caption = f"{hook} {val} {cp} {close} {hashtags}"
    # Add dual-path note (DM is frictionless, website for researchers)
    caption += " DM DEMO or link in bio — free 20-min setup, no commitment."
    return caption
