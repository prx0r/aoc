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
        "Your phone rang at 3pm. You were on a job. AI answered.",
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


# ── Deterministic generator (no LLM needed) ─────────────────

def generate_slides_deterministic(
    hook: str,
    audience: str = "electrician",
    template: str = "opportunity",
    slide_count: int = 6,
) -> SlideshowScript:
    """Generate slides without any LLM call.

    Returns a structured script with placeholder content based on template.
    """
    templates = {
        "opportunity": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="40% of UK sole traders already use AI", position=0.5, kind="proof"),
            SlideSpec(text="But only 18% have connected it to their business", position=0.5, kind="body"),
            SlideSpec(text="Missed calls. Late quotes. Lost jobs.", position=0.5, kind="body"),
            SlideSpec(text="AI can answer calls, send quotes, book jobs — while you're on the tools", position=0.5, kind="body"),
            SlideSpec(text="One setup. No subscription. £499.", position=0.5, kind="close"),
        ],
        "before_after": [
            SlideSpec(text=hook, position=0.35, kind="hook"),
            SlideSpec(text="Before: Missed 3 calls yesterday, sent quotes at 11pm", position=0.5, kind="body"),
            SlideSpec(text="After: AI answered all 3, sent quotes by 4pm", position=0.5, kind="body"),
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
            SlideSpec(text="Watch: A customer sends a WhatsApp at 2pm", position=0.5, kind="body"),
            SlideSpec(text="AI responds with a quote template in 30 seconds", position=0.5, kind="body"),
            SlideSpec(text="You approve on your phone between jobs", position=0.5, kind="body"),
            SlideSpec(text="Customer gets a professional quote by 2:15pm", position=0.5, kind="body"),
            SlideSpec(text="You never touched a keyboard.", position=0.5, kind="close"),
        ],
    }

    slides = templates.get(template, templates["opportunity"])
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
    """Get a random hook from the bank."""
    import random
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
