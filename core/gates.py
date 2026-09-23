"""Content gates — run BEFORE render. Failures become FAIL receipts.

Ported from /content/core/gates.py (evidence-fresh, no-duplicate,
claim-resolved) plus two render-specific gates (hook-quality, render-legible).
Fail-closed: run_carousel refuses to render on gate failure.
"""

from __future__ import annotations

import json
from pathlib import Path

# Buyer terms per segment: the hook must name one (or carry a number).
BUYER_TERMS = {
    "electrician": {"electrician", "electricians", "spark", "sparkie", "sparkies",
                    "quotes", "tools", "tradify", "job"},
    "beautician": {"salon", "chair", "booking", "no-show", "no-shows", "client"},
    "plumber": {"plumber", "plumbers", "boiler", "triage", "callout", "job"},
    "sole_trader": {"sole trader", "google", "whatsapp", "invoice", "customer"},
}


def gate_evidence_fresh(proof) -> tuple[bool, str]:
    if not proof.evidence_refs and not proof.claims:
        return False, "no claims at all"
    if not proof.observed_at:
        return False, "no observed_at"
    return True, f"{len(proof.evidence_refs)} evidence refs"


def gate_no_duplicate(content_id: str, template: str,
                      receipts_path: Path | str = "receipts/content.jsonl") -> tuple[bool, str]:
    p = Path(receipts_path)
    if not p.exists():
        return True, "novel (empty chain)"
    with open(p) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            d = r.get("data", {})
            if (d.get("content_id") == content_id
                    and r.get("event") == "carousel_built"):
                return False, f"already built (receipt {r.get('receipt_id')})"
    return True, "novel"


def gate_claim_resolved(plan: dict, proof) -> tuple[bool, str]:
    hook = plan.get("hook", "")
    close = plan.get("cta", "")
    known = set(proof.claims)
    for i, slide in enumerate(plan.get("slides", [])):
        text = slide.get("text", "")
        if not text:
            return False, f"slide {i} is empty"
        if text in (hook, close):
            continue
        if any(text == c or text in c or c in text for c in known if c):
            continue
        # plain workflow lines (no stats, no offer) pass as mechanism
        tl = text.lower()
        if not any(k in tl for k in ("%", "£", "$", "vs")):
            continue
        return False, f"slide {i} traces to nothing: {text[:60]}"
    return True, "claims resolve"


def gate_hook_quality(hook: str, segment: str) -> tuple[bool, str]:
    words = hook.split()
    if len(words) > 12:
        return False, f"hook too long ({len(words)} words, max 12)"
    terms = BUYER_TERMS.get(segment, set())
    hl = hook.lower()
    names_buyer = any(t in hl for t in terms)
    has_number = any(ch.isdigit() for ch in hook)
    asks = hook.rstrip().endswith("?")
    if not (names_buyer or has_number):
        return False, "hook names neither buyer nor number"
    if not (asks or has_number or "vs" in hl.lower()):
        return False, "hook has no question, number, or comparison"
    return True, "hook earns swipe 1"


def gate_render_legible(plan: dict) -> tuple[bool, str]:
    slides = plan.get("slides", [])
    n = len(slides)
    # +1 CTA slide gets appended at render; allow 4..8 pre-CTA
    if not (4 <= n <= 8):
        return False, f"{n} slides, need 4..8"
    for i, slide in enumerate(slides):
        words = len(slide.get("text", "").split())
        limit = 12 if slide.get("kind") == "hook" else 18
        if words > limit:
            return False, f"slide {i} has {words} words (max {limit})"
    kinds = [s.get("kind") for s in slides]
    if "close" not in kinds and "cta" not in str(plan.get("cta", "")).lower():
        pass  # CTA appended at render; presence checked post-render
    texts = [s.get("text", "") for s in slides]
    if len(set(texts)) != len(texts):
        return False, "duplicate slide text"
    return True, "legible"


def run_gates(plan: dict, proof, segment: str,
              receipts_path: Path | str = "receipts/content.jsonl") -> dict:
    results = {
        "evidence-fresh-v1": gate_evidence_fresh(proof),
        "no-duplicate-v1": gate_no_duplicate(plan.get("content_id", ""), plan.get("template", ""), receipts_path),
        "claim-resolved-v1": gate_claim_resolved(plan, proof),
        "hook-quality-v1": gate_hook_quality(plan.get("hook", ""), segment),
        "render-legible-v1": gate_render_legible(plan),
    }
    passed = all(ok for ok, _ in results.values())
    return {"passed": passed,
            "gates": {k: {"ok": ok, "detail": d} for k, (ok, d) in results.items()}}
