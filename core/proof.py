"""Proof — immutable source evidence. No carousel renders without one.

Ported from /content/core/proof.py. A plan becomes a Proof; plans whose
stat claims trace to nothing are refused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.ids import record_id


@dataclass(frozen=True)
class Proof:
    proof_id: str
    kind: str  # offer_claim | segment_skin
    source: str  # segments/<id>/proofs.yaml
    subject: str
    claims: list = field(default_factory=list)
    evidence_refs: list = field(default_factory=list)
    observed_at: str = ""
    # Replay invariant (ported from ographuk idempotence law):
    # same skin + same plan = same lineage_root.
    lineage_root: str = ""
    # Claims that resolved but need human review (pending status).
    pending_review: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"proof_id": self.proof_id, "kind": self.kind,
                "source": self.source, "subject": self.subject,
                "claims": self.claims, "evidence_refs": self.evidence_refs,
                "observed_at": self.observed_at,
                "lineage_root": self.lineage_root,
                "pending_review": self.pending_review}


def _load_registry() -> dict:
    """claims.yaml: claim_id -> record. Loaded once, cached on the function."""
    import yaml
    from pathlib import Path
    if not hasattr(_load_registry, "cache"):
        fp = Path(__file__).parent.parent / "claims.yaml"
        data = yaml.safe_load(fp.read_text()) if fp.exists() else {}
        _load_registry.cache = (data.get("claims") or {})
    return _load_registry.cache


def proof_from_plan(plan: dict, skin: dict) -> Proof:
    """A slide plan becomes a Proof. Untraced stat claims are refused.

    Resolution order per slide:
    1. Explicit claim_refs from the deck builder (exact claim_id).
    2. Exact text match against the registry (claim text contained either way).
    Number-overlap matching is DELETED: an invented 62%-of-customers claim
    must not resolve to an unrelated 62%-of-calls source. Unknown stat
    claims raise; unknown non-stat claims enter review via the receipt,
    never via fuzzy match.
    """
    registry = _load_registry()
    seg = plan.get("segment", "?")
    declared_refs = {(int(k) if str(k).isdigit() else k): v
                     for k, v in (plan.get("claim_refs") or {}).items()}
    close = (skin.get("profile", {}) or {}).get("close", "")
    hook = plan.get("hook", "")

    claims = [hook]
    evidence_refs = []
    pending_review = []
    for i, slide in enumerate(plan.get("slides", [])):
        text = slide.get("text", "")
        claims.append(text)
        ref = declared_refs.get(i)
        if ref and ref in registry:
            if _check_permitted(registry[ref], seg, text) == "pending":
                pending_review.append(ref)
            evidence_refs.append(_locator(seg, ref))
            continue
        if text == hook or text == close:
            continue
        if _is_stat_claim(text):
            match, state = _exact_match(text, registry, seg)
            if match is None:
                raise ValueError(f"stat claim traces to nothing: {text[:60]}")
            evidence_refs.append(match)
            if state == "pending":
                pending_review.append(match)

    pid = record_id("PROOF", {"id": plan.get("content_id"), "claims": claims})
    return Proof(
        proof_id=pid,
        kind="offer_claim",
        source=f"segments/{seg}/proofs.yaml",
        subject=plan.get("hook", "")[:60],
        claims=[c for c in claims if c],
        evidence_refs=sorted(set(evidence_refs)),
        observed_at=plan.get("created_at") or datetime.now(timezone.utc).isoformat(),
        lineage_root=record_id("PLAN", {"hook": plan.get("hook"),
                                        "slides": plan.get("slides"),
                                        "segment": seg,
                                        "skin_hash": plan.get("skin_hash")}),
        pending_review=sorted(set(pending_review)),
    )


def _is_stat_claim(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("%", "£", "$", "vs", "report", "survey", "costs", "study"))


def _check_permitted(record: dict, segment: str, text: str) -> str:
    """Returns 'approved' or 'pending'. Raises on rejected/unpermitted.

    Pending claims pass WITH a review note (unknown claims enter review,
    never fuzzy-match); rejected claims refuse.
    """
    permitted = record.get("permitted_segments") or []
    if permitted and segment not in permitted:
        raise ValueError(f"claim {record.get('claim_id')} not permitted "
                         f"for segment {segment}: {text[:60]}")
    status = record.get("status") or "approved"
    if status == "rejected":
        raise ValueError(f"claim {record.get('claim_id')} rejected: {text[:60]}")
    return "pending" if status == "pending" else "approved"


def _exact_match(text: str, registry: dict, segment: str) -> tuple[str | None, str]:
    """Exact text containment only — no number overlap, ever.

    Terminal punctuation is stripped first: "…per salon." and "…per salon"
    are the same claim. Anything beyond that needs an explicit registry
    wording, not fuzz. Returns (locator|None, approval state).
    """
    t = text.rstrip(".!?…").strip()
    for cid, record in registry.items():
        claim = (record.get("text") or "").rstrip(".!?…").strip()
        if not claim:
            continue
        if claim in t or t in claim:
            try:
                state = _check_permitted(record, segment, text)
            except ValueError:
                continue
            return _locator(segment, cid), state
    return None, ""


def _locator(segment: str, claim_id: str) -> str:
    """Locator form: segments/<id>/proofs.yaml#/proofs/<index>/id, or
    claims.yaml#/<claim_id> for cross-segment/offer claims."""
    if "/" in claim_id or claim_id.startswith("offer."):
        return f"claims.yaml#/{claim_id}"
    # claim_ids are namespaced {segment}.{proof_id}; strip to index the skin
    bare = claim_id.split(".", 1)[1] if claim_id.startswith(segment + ".") else claim_id
    import yaml
    from pathlib import Path
    fp = Path(__file__).parent.parent / "segments" / segment / "proofs.yaml"
    try:
        proofs = (yaml.safe_load(fp.read_text()).get("proofs") or [])
    except OSError:
        return f"claims.yaml#/{claim_id}"
    for i, p in enumerate(proofs):
        if p.get("id") == bare:
            return f"segments/{segment}/proofs.yaml#/proofs/{i}/id"
    return f"claims.yaml#/{claim_id}"


def _best_match(text: str, proofs: list[dict]) -> str | None:
    """DELETED — number-overlap matching removed per peer review.

    Kept as a tombstone so any lingering caller fails loudly instead of
    silently fuzzy-matching. An invented 62% claim must never resolve to
    an unrelated 62% source.
    """
    raise NotImplementedError(
        "_best_match (number-overlap) was removed: use explicit claim_refs "
        "or exact registry text matches only")


def _matches_known(text: str, known: list[str]) -> bool:
    raise NotImplementedError(
        "_matches_known was removed with number-overlap matching")
