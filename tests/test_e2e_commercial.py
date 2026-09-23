"""E2E fictional scenarios — full commercial chain per review §4.

Three scenarios, all FICTIONAL data (never real customers):
1. nails Quickstart waiting-list campaign
2. cleaners Quickstart campaign
3. electrician £499 campaign

Each exercises: offer ingestion → render → rejection/revision →
approval → manual publication confirmation → metrics → simulated sale.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import acquisition as A  # noqa: E402
from core.carousel import run_carousel  # noqa: E402


def _chain(tmp_path, hook, template, segment, cta, kind="organic"):
    from core.carousel import run_carousel as _run
    from core.review import sign_off
    r = _run(hook, template, base_dir=tmp_path / "store",
             receipts_path=tmp_path / "r.jsonl", segment=segment,
             cta=cta, kind=kind)
    out = Path(r["out_dir"])
    # review + approve the exact revision
    sign_off(tmp_path / "r.jsonl", r["plan"]["content_id"], "approved",
             "e2e fictional sign-off", reviewer="e2e",
             store_dir=tmp_path / "store")
    assert (out / "tiktok_carousel.zip").exists()
    return r


def test_e2e_nails_waitlist_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    r = _chain(tmp_path,
               "Just downloaded Muse? We'll set it up for your business for £20.",
               "waitlist", "nails",
               "DM NAILS to join the UK list.")
    assert "UK list" in r["manifest"]["final_cta"]
    # publish confirm path: drive the lifecycle in the test DB
    from core.store import session as _session, set_status as _set
    with _session() as db:
        _set(db, r["plan"]["content_id"], "approved", actor="human")
        _set(db, r["plan"]["content_id"], "ready_for_manual_post", actor="human")
        _set(db, r["plan"]["content_id"], "published_confirmed", actor="human")
    # simulated sale through the funnel
    A.record_lead("E2E-N1", source="tiktok-organic", campaign_id="C-N",
                  creative_id=r["plan"]["content_id"][:24],
                  permission_status="consented", permission_ref="e2e-form-1")
    A.record_qualification("E2E-N1", True, is_owner_manager=True,
                           business_type="nail-tech", stated_need="booking")
    A.record_conversion("E2E-N1", amount_gbp=20.0, paid_at="2026-09-23T10:00:00")
    f = A.funnel("C-N")
    assert (f["leads"], f["qualified"], f["paid"]) == (1, 1, 1)


def test_e2e_cleaners_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    r = _chain(tmp_path,
               "Cleaners — which paused plan would you win back first?",
               "retention", "cleaners",
               "DM CLEAN for £20 setup.")
    assert "£20" in r["manifest"]["final_cta"]
    A.record_lead("E2E-C1", source="facebook-paid", campaign_id="C-C",
                  permission_status="consented", permission_ref="e2e-form-2")
    A.record_qualification("E2E-C1", False, business_type="cleaner",
                           stated_need="not-owner")
    f = A.funnel("C-C")
    assert (f["leads"], f["qualified"], f["paid"]) == (1, 0, 0)


def test_e2e_electrician_499_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    r = _chain(tmp_path,
               "Landlords need EICRs every 5 years. Who owns that cycle?",
               "annuity", "electrician",
               "DM QUOTE — UK electricians only. £499 setup.", kind="ad")
    assert "£499" in r["manifest"]["final_cta"]
    assert r["plan"]["offer_id"] == "standard-ai-setup"
    A.record_lead("E2E-E1", source="direct-call", campaign_id="C-E",
                  permission_status="consented", permission_ref="e2e-call-3")
    A.record_qualification("E2E-E1", True, is_owner_manager=True,
                           business_type="electrical-contractor",
                           stated_need="missed-calls")
    A.record_conversion("E2E-E1", amount_gbp=499.0, paid_at="2026-09-23T11:00:00")
    f = A.funnel("C-E")
    assert f["revenue_gbp"] == 499.0
