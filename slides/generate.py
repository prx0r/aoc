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
    # slide index -> registry claim_id. Explicit references, never fuzzy.
    claim_refs: dict = field(default_factory=dict)


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

SEGMENT_IDS = ["electrician", "beautician", "plumber", "sole_trader",
                 "nails", "lashes", "hair", "cleaners", "dog_groomers",
                 "gardeners", "car_detailers", "driving_instructors", "weddings"]
_SEG_CACHE: dict = {}


def _shorten(text: str, n: int = 15) -> str:
    """Trim to ~n words for body slides. Strips parenthetical caveats first."""
    import re
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    words = text.split()
    return " ".join(words[:n]) if len(words) > n else text


def _mid_sentence(text: str) -> str:
    """Lowercase the first letter for mid-sentence use — unless it's an
    acronym (AI, SMS, GBP, EICR...). Blind lowercasing printed 'al triages'."""
    import re
    m = re.match(r"([A-Za-z]+)(.*)$", text, re.DOTALL)
    if not m:
        return text
    first, rest = m.group(1), m.group(2)
    if first.isupper() and len(first) <= 4:
        return text
    return first[:1].lower() + first[1:] + rest


def _skin_claims(skin: dict, segment: str = "") -> list[tuple[str, str]]:
    """Non-offer proof claims as (registry claim_id, text).

    IDs are namespaced {segment}.{proof_id} — matching claims.yaml.
    """
    proofs = (skin.get("proofs", {}) or {}).get("proofs", []) or []
    seg = segment or skin.get("id", "")
    return [(f"{seg}.{p.get('id')}", p.get("claim", "")) for p in proofs
            if p.get("id") != "offer_pilot" and p.get("claim")]


def _skin_pains(skin: dict) -> list[str]:
    profile = skin.get("profile", {}) or {}
    return [str(p) for p in (profile.get("pains") or []) if p]


def _generic_deck(skin: dict, hook: str, template: str) -> list[SlideSpec] | None:
    """Build deck purely from skin data. No hardcoded trade copy.

    Explicit _SEGMENT_DECKS win where hand-tuned; everything else falls
    here so new skins never leak another trade's words.
    """
    profile = skin.get("profile", {}) or {}
    seg = skin.get("id", "")
    pains = _skin_pains(skin)
    claim_pairs = _skin_claims(skin, seg)
    close = profile.get("close", "")
    workflow = profile.get("workflow", "Triaged, drafted, reminded — you approve everything.")
    comparator = profile.get("comparator", "the old way")
    dm_keyword = profile.get("dm_keyword", "SETUP")

    def _claim_text(i: int, fallback: str) -> tuple[str, str]:
        # returns (text, registry claim_id or "")
        if i < len(claim_pairs):
            cid, text = claim_pairs[i]
            return _shorten(text), cid
        return fallback, ""

    c0, r0 = _claim_text(0, _shorten(pains[0]) if pains else "")
    c1, r1 = _claim_text(1, _shorten(pains[1]) if len(pains) > 1 else "")
    p0 = _shorten(pains[0]) if pains else ""
    p1 = _shorten(pains[1]) if len(pains) > 1 else p0
    # slide index (post-hook) -> registry claim_id for proof-kind slides
    refs = {1: r0, 2: r1}

    builders = {
        "opportunity": [
            ("hook", hook, 0.35), ("proof", c0, 0.5), ("body", c1, 0.5),
            ("body", p0, 0.5), ("body", workflow, 0.5), ("close", close, 0.5),
        ],
        "before_after": [
            ("hook", hook, 0.35), ("body", f"Before: {p0}", 0.5),
            ("body", f"After: {workflow}", 0.5), ("body", f"Before: {p1}", 0.5),
            ("body", f"After: handled systematically, approved by you.", 0.5),
            ("close", close, 0.5),
        ],
        "faq": [
            ("hook", hook, 0.35), ("body", f"Q: {p0}?", 0.5),
            ("body", f"A: {workflow}", 0.5), ("body", f"Q: {p1}?", 0.5),
            ("body", "A: Set up for you. Training included.", 0.5),
            ("close", close, 0.5),
        ],
        "social_proof": [
            ("hook", hook, 0.35), ("proof", c0, 0.5), ("proof", c1, 0.5),
            ("body", p0, 0.5), ("close", close, 0.5),
        ],
        "demo": [
            ("hook", hook, 0.35), ("body", "Watch: an enquiry lands (fictional demo)", 0.5),
            ("body", workflow, 0.5),
            ("body", "You approve on your phone between jobs", 0.5),
            ("body", "Customer gets a pro response in minutes", 0.5),
            ("close", "Nothing sends without your approval.", 0.5),
        ],
        "diagnostic": [
            ("hook", hook, 0.35), ("body", p0 + "?", 0.5), ("body", p1 + "?", 0.5),
            ("body", "That's not workload. It's triage.", 0.5),
            ("body", workflow, 0.5), ("close", close, 0.5),
        ],
        "teardown": [
            ("hook", hook, 0.35), ("body", p0 + ".", 0.5), ("body", p1 + ".", 0.5),
            ("body", "The fix isn't trying harder. It's triage + drafts.", 0.5),
            ("body", workflow, 0.5), ("close", close, 0.5),
        ],
        "comparison": [
            ("hook", hook, 0.35),
            ("body", f"{comparator}: you still do the admin.", 0.5),
            ("body", f"AI Onboard: {_mid_sentence(workflow)}", 0.5),
            ("body", "Question: who does the work — you, or the system?", 0.5),
            ("body", "We don't replace tools. We run them.", 0.5),
            ("close", close, 0.5),
        ],
        "annuity": [
            ("hook", hook, 0.35),
            ("proof", c0, 0.5),
            ("body", "One job becomes a cycle. Cycles become revenue.", 0.5),
            ("body", workflow, 0.5),
            ("body", "Compliance-driven work doesn't churn.", 0.5),
            ("close", close, 0.5),
        ],
        "retention": [
            ("hook", hook, 0.35),
            ("proof", c0, 0.5),
            ("body", "Paused isn't lost. Lapsed isn't gone.", 0.5),
            ("body", workflow, 0.5),
            ("body", "Win-back lists, ready for your approval.", 0.5),
            ("close", close, 0.5),
        ],
        "waitlist": [
            ("hook", hook, 0.35),
            ("body", "Muse launched in the US on Sep 8. UK date unconfirmed.", 0.5),
            ("body", "The UK list gets first installs when it lands.", 0.5),
            ("body", workflow, 0.5),
            ("body", "One assisted setup. 7 days support. Personal manual.", 0.5),
            ("close", f"DM {dm_keyword} to join the UK list.", 0.5),
        ],
        "trust": [
            ("hook", hook, 0.35),
            ("body", "We never ask for passwords — you log in, you grant, you revoke.", 0.5),
            ("body", "Every outbound message needs your explicit approval first.", 0.5),
            ("body", "You keep your accounts, your passwords, your money.", 0.5),
            ("body", "Revocation takes effect immediately. No call needed.", 0.5),
            ("close", close, 0.5),
        ],
    }
    def _overlap(a: str, b: str) -> float:
        import re
        wa = set(re.findall(r"[a-z0-9]+", a.lower())) - {"the", "a", "an", "to", "of", "and", "or"}
        wb = set(re.findall(r"[a-z0-9]+", b.lower())) - {"the", "a", "an", "to", "of", "and", "or"}
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    spec = builders.get(template)
    if not spec or not close:
        return None
    proof_texts = {c0: r0, c1: r1} if (c0 or c1) else {}
    slides, seen, refs = [], [], {}
    for k, t, pos in spec:
        # dedupe: exact or near-duplicate (>60% word overlap) slides read as
        # repetition on a contact sheet — the human eye catches what word
        # counts miss, so the builder refuses to emit them
        if not t or t in seen or any(_overlap(t, s) > 0.6 for s in seen):
            continue
        seen.append(t)
        if k == "proof" and t in proof_texts and proof_texts[t]:
            refs[len(slides)] = proof_texts[t]
        slides.append(SlideSpec(text=t, position=pos, kind=k))
    # keep the close last even if an earlier identical line was dropped
    if slides and slides[-1].kind != "close" and close not in seen:
        slides.append(SlideSpec(text=close, position=0.5, kind="close"))
    if len(slides) < 5:
        return None
    return slides, refs


def _segments_root() -> Path:
    return Path(__file__).parent.parent / "segments"


def load_segment(segment: str) -> dict:
    """Load a segment skin. Unknown segments RAISE — a misspelled segment
    must never silently produce another trade's copy (peer review P1)."""
    if segment in _SEG_CACHE:
        return _SEG_CACHE[segment]
    root = _segments_root()
    if not (root / segment).exists():
        known = sorted(p.name for p in root.iterdir() if p.is_dir())
        raise ValueError(f"unknown segment: {segment!r} (known: {known})")
    import yaml
    skin = {"id": segment}
    for name in ("profile", "hooks", "proofs", "templates"):
        fp = root / segment / f"{name}.yaml"
        skin[name] = yaml.safe_load(fp.read_text()) if fp.exists() else {}
    _SEG_CACHE[segment] = skin
    return skin


def get_hooks(segment: str = "electrician") -> list[dict]:
    """Hook bank for a segment. Unknown segments raise (no silent fallback)."""
    hooks = load_segment(segment).get("hooks", {}).get("hooks", [])
    if hooks:
        return hooks
    return [{"text": h, "angle": "bank", "audience": segment}
            for h in HOOK_BANK.get(segment, HOOK_BANK["general"])]


def segment_close(segment: str = "electrician") -> str:
    return load_segment(segment).get("profile", {}).get("close", "")


def skin_hash(segment: str = "electrician") -> str:
    """Hash of the segment skin bundle. Any skin edit changes future IDs.

    Same skin + same plan = same proof (replay invariant).
    """
    import hashlib
    root = _segments_root() / segment
    h = hashlib.sha256()
    for name in ("profile", "hooks", "proofs", "templates"):
        fp = root / f"{name}.yaml"
        h.update(name.encode())
        h.update(fp.read_bytes() if fp.exists() else b"")
    return h.hexdigest()


# Explicit per-segment decks for the two highest-use templates.
# (segment, template) -> list of slide bodies (hook prepended by caller).
_SEGMENT_DECKS: dict[tuple[str, str], list[str]] = {
    ("beautician", "opportunity"): [
        "No-shows cost ~£19K/year per salon.",
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
        "40% of sole traders use AI, only 18% integrated it.",
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

    # 1. Explicit hand-tuned deck wins.
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

    # 2. Generic skin-driven deck (no hardcoded trade copy).
    try:
        generic_out = _generic_deck(load_segment(audience), hook, template)
    except Exception:
        generic_out = None
    if generic_out:
        generic, refs = generic_out
        # claim_refs survive slide_count truncation only for kept slides
        kept = generic[:slide_count]
        kept_texts = {s.text for s in kept}
        # remap refs by surviving index
        new_refs = {}
        for i, s in enumerate(kept):
            for j, t in enumerate(generic):
                if t.text == s.text and j in refs:
                    new_refs[i] = refs[j]
                    break
        return SlideshowScript(
            hook=hook,
            slides=kept,
            template=template,
            audience=audience,
            claim_refs=new_refs,
        )

    # 3. Legacy electrician decks (electrician segment only — never leaks).
    if audience != "electrician":
        raise ValueError(f"no deck for segment={audience} template={template}")
    slides = templates.get(template, templates["opportunity"])
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
        "claim_refs": {str(k): v for k, v in script.claim_refs.items()},
    }
