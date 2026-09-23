"""Offer registry — versioned, machine-readable contract for generation.

Snapshotted from aionboard OFFER.md (see offers.yaml `source.commit`).
Generation reads THIS, never prose docs. An upstream offer change bumps
the version here, which invalidates pending creatives (revalidation gate)
while leaving history reproducible against its original version.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).parent.parent / "offers.yaml"
_cache: dict | None = None


def load_registry(path: Path | str = REGISTRY_PATH) -> dict:
    global _cache
    if _cache is not None and str(path) == str(REGISTRY_PATH):
        return _cache
    data = yaml.safe_load(Path(path).read_text())
    if _cache is None and str(path) == str(REGISTRY_PATH):
        _cache = data
    return data


def get_offer(offer_id: str) -> dict:
    reg = load_registry()
    offers = reg.get("offers", {})
    if offer_id not in offers:
        raise ValueError(f"unknown offer: {offer_id}")
    return offers[offer_id]


def offer_for_segment(segment: str) -> tuple[str, dict]:
    """Which offer a segment sells. Returns (offer_id, offer)."""
    reg = load_registry()
    for offer_id, offer in reg.get("offers", {}).items():
        if segment in (offer.get("eligible_segments") or []):
            return offer_id, offer
    raise ValueError(f"no offer covers segment: {segment}")


def permitted_cta(segment: str, kind: str = "organic") -> str:
    """The CTA family a segment may use right now.

    Quickstart with availability=waitlist forces waitlist CTAs —
    taking £20 for Muse-specific installation before UK access exists
    would sell something undeliverable.
    """
    offer_id, offer = offer_for_segment(segment)
    if offer.get("availability") == "waitlist":
        return "waitlist"
    return "enquiry"


def check_revalidation(plan: dict, registry: dict | None = None) -> tuple[bool, str]:
    """Does this plan's offer version still match the registry?

    Plans stamp offer_id + offer_version at build. A registry bump means
    upstream changed the offer → pending creatives need revalidation,
    history stays reproducible against its recorded version.
    """
    reg = registry or load_registry()
    offer_id = plan.get("offer_id")
    if not offer_id:
        return False, "plan has no offer_id (built before offer registry)"
    current = (reg.get("offers", {}).get(offer_id) or {}).get("version")
    if current is None:
        return False, f"offer {offer_id} no longer exists"
    if plan.get("offer_version") != current:
        return False, (f"offer {offer_id} v{plan.get('offer_version')} "
                       f"stale vs registry v{current} — revalidate")
    return True, f"offer {offer_id} v{current} current"


def forbidden_claim_present(text: str, segment: str) -> str | None:
    """Return the forbidden claim found in text, or None."""
    _, offer = offer_for_segment(segment)
    tl = text.lower()
    for claim in offer.get("forbidden_claims", []):
        if claim.lower() in tl:
            return claim
    return None
