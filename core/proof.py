"""Proof — immutable source evidence. No carousel renders without one.

Ported from /content/core/proof.py. A plan becomes a Proof; plans whose
stat claims trace to nothing are refused.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Proof:
    proof_id: str
    kind: str  # offer_claim | segment_skin
    source: str  # segments/<id>/proofs.yaml
    subject: str
    claims: list = field(default_factory=list)
    evidence_refs: list = field(default_factory=list)
    observed_at: str = ""

    def to_dict(self) -> dict:
        return {"proof_id": self.proof_id, "kind": self.kind,
                "source": self.source, "subject": self.subject,
                "claims": self.claims, "evidence_refs": self.evidence_refs,
                "observed_at": self.observed_at}


def proof_from_plan(plan: dict, skin: dict) -> Proof:
    """A slide plan becomes a Proof. Untraced stat claims are refused.

    Every slide containing a number (%, £, $) or the words 'costs'/'report'
    must match a proofs.yaml claim or the segment close line. The hook and
    plain workflow lines pass by construction (they're the offer, not stats).
    """
    proofs = (skin.get("proofs", {}) or {}).get("proofs", []) or []
    known_claims = [p.get("claim", "") for p in proofs]
    close = (skin.get("profile", {}) or {}).get("close", "")
    hook = plan.get("hook", "")

    claims = [hook]
    evidence_refs = []
    for slide in plan.get("slides", []):
        text = slide.get("text", "")
        claims.append(text)
        for p in proofs:
            claim = p.get("claim", "")
            if claim and (claim in text or text in claim):
                evidence_refs.append(p.get("id", ""))
                break
        else:
            if text == hook or text == close:
                continue
            if _is_stat_claim(text):
                match = _best_match(text, proofs)
                if match is None:
                    raise ValueError(f"stat claim traces to nothing: {text[:60]}")
                evidence_refs.append(match)

    pid = "proof_" + hashlib.sha1(json.dumps(
        {"id": plan.get("content_id"), "claims": claims},
        sort_keys=True).encode()).hexdigest()[:12]
    return Proof(
        proof_id=pid,
        kind="offer_claim",
        source=f"segments/{plan.get('segment', '?')}/proofs.yaml",
        subject=plan.get("hook", "")[:60],
        claims=[c for c in claims if c],
        evidence_refs=sorted(set(evidence_refs)),
        observed_at=plan.get("created_at") or datetime.now(timezone.utc).isoformat(),
    )


def _is_stat_claim(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("%", "£", "$", "vs", "report", "survey", "costs", "study"))


def _matches_known(text: str, known: list[str]) -> bool:
    return _best_match(text, [{"claim": k} for k in known]) is not None


def _best_match(text: str, proofs: list[dict]) -> str | None:
    """Return the id of the proof whose claim best matches the slide text."""
    import re
    tl = text.lower()
    for p in proofs:
        kl = (p.get("claim") or "").lower()
        if not kl:
            continue
        if kl in tl or tl in kl:
            return p.get("id", "")
        tn = set(re.findall(r"\d+", tl))
        kn = set(re.findall(r"\d+", kl))
        if tn and tn & kn:
            return p.get("id", "")
    return None
