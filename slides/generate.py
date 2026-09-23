"""Slide copy generator — LLM-based or deterministic fallback.

Generates TikTok photo-mode carousel scripts from hooks/offers.
Each slide: text (10 words max for hooks, 15 for body) + position + tags.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class SlideSpec:
    text: str
    position: float = 0.7
    tags: list[str] = field(default_factory=list)
    kind: str = "body"  # hook, body, proof, close


@dataclass
class SlideshowScript:
    hook: str
    slides: list[SlideSpec]
    template: str = "opportunity"
    audience: str = "electrician"
    cta: str = ""


# ── Hook bank (tested patterns) ─────────────────────────────

HOOK_BANK = {
    "electrician": [
        "UK electricians — still doing quotes at 9pm?",
        "Which of these would you automate first?",
        "Your competitors are using AI. Are you?",
        "The quote you sent at 11pm — AI could've sent it at 2pm",
        "Am I doing this wrong?",
        "What would you automate first?",
        "62% of calls missed while on tools. Here's the fix.",
        "Your phone rang at 3pm. The follow-up was drafted by 3:05.",
        "£499 to never miss another enquiry. Worth it?",
        "The electrician who answers first — wins the job.",
    ],
    "general": [
        "What if your business ran itself while you worked?",
        "The task you keep postponing — AI can do it in 2 minutes",
        "You're paying for software you're not using",
        "Stop doing £10/hour work when you charge £50/hour",
    ],
}


# ── Segment skins (core engine, per-trade copy) ─────────────
# Shape stolen from /content gardens: engine is generic, skins supply copy.
# segments/<id>/{profile,hooks,proofs,templates}.yaml

SEGMENT_IDS = ["electrician", "beautician", "plumber", "sole_trader"]
_SEG_CACHE: dict = {}


def _segments_root() -> Path:
    return Path(__file__).parent.parent / "segments"


def load_segment(segment: str) -> dict:
    """Load a segment skin. Falls back to electrician for unknown ids."""
    if segment in _SEG_CACHE:
        return _SEG_CACHE[segment]
    root = _segments_root()
    sid = segment if (root / segment).exists() else "electrician"
    import yaml
    skin = {"id": sid}
    for name in ("profile", "hooks", "proofs", "templates"):
        fp = root / sid / f"{name}.yaml"
        skin[name] = yaml.safe_load(fp.read_text()) if fp.exists() else {}
    _SEG_CACHE[segment] = skin
    return skin


def get_hooks(segment: str = "electrician") -> list[dict]:
    """Hook bank for a segment (skin file, fallback to builtin bank)."""
    try:
        hooks = load_segment(segment).get("hooks", {}).get("hooks", [])
        if hooks:
            return hooks
    except Exception:
        pass
    return [{"text": h, "angle": "bank", "audience": segment}
            for h in HOOK_BANK.get(segment, HOOK_BANK["general"])]


def segment_close(segment: str = "electrician") -> str:
    try:
        return load_segment(segment).get("profile", {}).get("close", "")
    except Exception:
        return ""


# Explicit per-segment decks for the two highest-use templates.
# (segment, template) -> list of slide bodies (hook prepended by caller).
_SEGMENT_DECKS: dict[tuple[str, str], list[str]] = {
    ("beautician", "opportunity"): [
        "No-shows cost ~£10K a year per chair.",
        "Deposit + reminder workflows, prepared in your booking platform.",
        "Lapsed-client win-back lists, ready for your approval.",
        "Booking triage set up day one. You approve every send.",
    ],
    ("beautician", "before_after"): [
        "Before: gaps Tue afternoons, chasing deposits by text.",
        "After: deposits taken at booking, reminders automatic.",
        "Before: regulars drift off, never rebooked.",
        "After: win-back engine fills the gaps.",
    ],
    ("plumber", "opportunity"): [
        "Emergency or routine — triage decides the day.",
        "AI triages enquiries, prepares bookings and reminders.",
        "Service-due lists chase repeat revenue.",
        "Quotes drafted on jobs. You approve everything.",
    ],
    ("plumber", "before_after"): [
        "Before: callouts chaos, quotes at 10pm.",
        "After: triaged diary, quotes drafted by 3pm.",
        "Before: services overdue, revenue lost.",
        "After: service-due reminders book the work.",
    ],
    ("sole_trader", "opportunity"): [
        "40% use AI. Only 18% connected it to the business.",
        "WhatsApp + notebook + inbox is not a system.",
        "Findable on Google. Bookable. Paid. Done.",
        "One setup. Training included. No subscription.",
    ],
    ("sole_trader", "before_after"): [
        "Before: invisible on Google, quotes at midnight.",
        "After: profile + site + chat. Enquiries triaged.",
        "Before: one-and-done customers.",
        "After: follow-ups and reviews automatic.",
    ],
}


# ── Deterministic generator (no LLM needed) ─────────────────

def generate_slides_deterministic(
    hook: str,
    audience: str = "electrician",
    template: str = "opportunity",
    slide_count: int = 6,
) -> SlideshowScript:
    """Generate slides without any LLM call.

    Segment-aware: explicit per-segment decks win; otherwise the generic
    electrician deck with the segment's close line substituted.
    """
    templates = {
        "opportunity": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="40% of UK sole traders already use AI", position=0.5, kind="proof"),
            SlideSpec(text="But only 18% have connected it to their business", position=0.5, kind="body"),
            SlideSpec(text="Missed calls. Late quotes. Lost jobs.", position=0.5, kind="body"),
            SlideSpec(text="AI triages enquiries, drafts quotes — you approve everything", position=0.5, kind="body"),
            SlideSpec(text="One setup. No subscription. £499.", position=0.5, kind="close"),
        ],
        "before_after": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Before: Missed 3 calls yesterday, sent quotes at 11pm", position=0.5, kind="body"),
            SlideSpec(text="After: all 3 triaged, quotes drafted by 4pm, you approved", position=0.5, kind="body"),
            SlideSpec(text="Before: Spent Sundays doing admin", position=0.5, kind="body"),
            SlideSpec(text="After: AI handles invoicing, scheduling, follow-ups", position=0.5, kind="body"),
            SlideSpec(text="Same electrician. Same business. Different tools.", position=0.5, kind="close"),
        ],
        "faq": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Q: Will AI replace electricians?", position=0.5, kind="body"),
            SlideSpec(text="A: No. AI replaces the admin. You do the work.", position=0.5, kind="body"),
            SlideSpec(text="Q: Is it hard to set up?", position=0.5, kind="body"),
            SlideSpec(text="A: We do it for you. 1 hour. Done.", position=0.5, kind="body"),
            SlideSpec(text="Q: What if I'm not tech-savvy?", position=0.5, kind="body"),
            SlideSpec(text="A: If you can use WhatsApp, you can use this.", position=0.5, kind="close"),
        ],
        "social_proof": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="73% of UK trades businesses are on social media", position=0.5, kind="proof"),
            SlideSpec(text="72% report skilled-labour shortages", position=0.5, kind="proof"),
            SlideSpec(text="The businesses that adapt — win", position=0.5, kind="body"),
            SlideSpec(text="AI Onboard: We set you up. You get back to work.", position=0.5, kind="close"),
        ],
        "demo": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Watch: an enquiry lands at 2pm (fictional demo)", position=0.5, kind="body"),
            SlideSpec(text="AI drafts a quote from your price book in 30 seconds", position=0.5, kind="body"),
            SlideSpec(text="You approve on your phone between jobs", position=0.5, kind="body"),
            SlideSpec(text="Customer gets a professional quote by 2:15pm", position=0.5, kind="body"),
            SlideSpec(text="Nothing sends without your approval.", position=0.5, kind="close"),
        ],
        "diagnostic": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="3 unread enquiries from yesterday?", position=0.5, kind="body"),
            SlideSpec(text="Quotes sent after 10pm?", position=0.5, kind="body"),
            SlideSpec(text="That's not workload. It's triage.", position=0.5, kind="body"),
            SlideSpec(text="AI triages, drafts, reminds. You approve.", position=0.5, kind="body"),
            SlideSpec(text="DM DIAGNOSIS — free setup score.", position=0.5, kind="close"),
        ],
        "teardown": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Day 3: lost a job to a faster quote.", position=0.5, kind="body"),
            SlideSpec(text="Day 11: double-booked Tuesday.", position=0.5, kind="body"),
            SlideSpec(text="Day 20: invoices unsent.", position=0.5, kind="body"),
            SlideSpec(text="The fix isn't trying harder. It's triage + drafts.", position=0.5, kind="body"),
            SlideSpec(text="Installed in ~1 hour. DM TEARDOWN.", position=0.5, kind="close"),
        ],
        "comparison": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Tradify: great job management. You do the admin.", position=0.5, kind="body"),
            SlideSpec(text="AI Onboard: connects Tradify + email + calendar.", position=0.5, kind="body"),
            SlideSpec(text="Question: who does the work — you, or the system?", position=0.5, kind="body"),
            SlideSpec(text="We don't replace Tradify. We run it.", position=0.5, kind="body"),
            SlideSpec(text="Already on Tradify? DM CONNECT.", position=0.5, kind="close"),
        ],
    }

    # Segment override: explicit deck wins (hook + bodies + segment close).
    key = (audience, template)
    if key in _SEGMENT_DECKS:
        bodies = _SEGMENT_DECKS[key]
        slides = [SlideSpec(text=hook, position=0.35, kind="hook")]
        for b in bodies:
            slides.append(SlideSpec(text=b, position=0.5, kind="body"))
        close = segment_close(audience)
        if close:
            slides.append(SlideSpec(text=close, position=0.5, kind="close"))
        return SlideshowScript(
            hook=hook, slides=slides[:slide_count],
            template=template, audience=audience,
        )

    slides = templates.get(template, templates["opportunity"])
    # Substitute segment close line so generic decks don't leak electrician CTA.
    slides = list(slides)
    close = segment_close(audience)
    if close and slides and slides[-1].kind == "close":
        slides[-1] = SlideSpec(text=close, position=0.5, kind="close")
    return SlideshowScript(
        hook=hook,
        slides=slides[:slide_count],
        template=template,
        audience=audience,
    )


# ── LLM generator (optional, better quality) ────────────────

def generate_slides_llm(
    hook: str,
    audience: str = "electrician",
    template: str = "opportunity",
    slide_count: int = 6,
    api_key: str = "",
    base_url: str = "https://openrouter.ai/api/v1",
    model: str = "anthropic/claude-3-haiku",
) -> SlideshowScript:
    """Generate slides using an LLM.

    Falls back to deterministic if no API key or LLM fails.
    """
    if not api_key:
        return generate_slides_deterministic(hook, audience, template, slide_count)

    system_prompt = f"""You are a TikTok carousel copywriter for {audience} businesses.
Write {slide_count} slides for a photo-mode carousel.

Rules:
- Slide 1 = scroll-stopping hook (under 10 words, bold claim or question)
- Slides 2-{slide_count-1} = ONE specific idea per slide, max 15 words
- Last slide = twist/punchline or clear CTA
- No hashtags, no emojis, natural sentence case
- Tone: direct, slightly provocative, no corporate speak

Output JSON: {{"slides": [{{"text": "...", "kind": "hook|body|proof|close"}}]}}"""

    user_prompt = f"Hook: {hook}\nTemplate: {template}"

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = json.loads(data["choices"][0]["message"]["content"])

        slides = [
            SlideSpec(text=s["text"], kind=s.get("kind", "body"))
            for s in content.get("slides", [])
        ]

        return SlideshowScript(
            hook=hook,
            slides=slides[:slide_count],
            template=template,
            audience=audience,
        )

    except Exception:
        # Fallback to deterministic
        return generate_slides_deterministic(hook, audience, template, slide_count)


# ── Utility ──────────────────────────────────────────────────

def get_random_hook(audience: str = "electrician") -> str:
    """Get a random hook from the segment skin."""
    import random
    hooks = [h["text"] for h in get_hooks(audience) if h.get("text")]
    if not hooks:
        hooks = HOOK_BANK.get(audience, HOOK_BANK["general"])
    return random.choice(hooks)


def script_to_json(script: SlideshowScript) -> dict:
    """Convert script to JSON-serializable dict."""
    return {
        "hook": script.hook,
        "template": script.template,
        "audience": script.audience,
        "cta": script.cta,
        "slides": [
            {"text": s.text, "position": s.position, "kind": s.kind, "tags": s.tags}
            for s in script.slides
        ],
    }
