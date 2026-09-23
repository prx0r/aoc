"""Campaign lifecycle tests: create → link → post → observe → funnel.

All data fictional. DB isolated per test via conftest AOC_DB.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _build(tmp_path, hook="Nail techs — DMs at midnight, booking at 9am?",
           template="opportunity", segment="nails"):
    from core.carousel import run_carousel
    return run_carousel(hook, template, base_dir=tmp_path / "store",
                        receipts_path=tmp_path / "r.jsonl", segment=segment)


def test_campaign_create_and_duplicate_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("AOC_RECEIPTS", str(tmp_path / "r.jsonl"))
    from core.acquisition import create_campaign
    c = create_campaign("test-camp-1", "nails", "muse-quickstart", 1,
                        hypothesis="h", budget_gbp=0, channel="tiktok")
    assert c["campaign_id"] == "test-camp-1"
    try:
        create_campaign("test-camp-1", "nails", "muse-quickstart", 1)
    except ValueError as e:
        assert "exists" in str(e)
    else:
        raise AssertionError("duplicate campaign accepted")


def test_campaign_rejects_unknown_segment_and_offer(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_server import aoc_campaign
    r = aoc_campaign("x", "nonsense-seg", "muse-quickstart")
    assert "error" in r and "unknown segment" in r["error"]
    r = aoc_campaign("x", "nails", "no-such-offer")
    assert "error" in r and "unknown offer" in r["error"]


def test_link_refuses_unapproved_creative(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("AOC_RECEIPTS", str(tmp_path / "r.jsonl"))
    from core.acquisition import create_campaign, link_creative
    r = _build(tmp_path)
    cid = r["plan"]["content_id"]
    create_campaign("test-camp-2", "nails", "muse-quickstart", 1)
    try:
        link_creative("test-camp-2", cid)
    except ValueError as e:
        assert "approval" in str(e)
    else:
        raise AssertionError("unapproved creative linked")


def test_link_unknown_campaign_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("AOC_RECEIPTS", str(tmp_path / "r.jsonl"))
    from core.acquisition import link_creative
    try:
        link_creative("nope", "AOC:anything")
    except ValueError as e:
        assert "unknown campaign" in str(e)
    else:
        raise AssertionError("link to unknown campaign accepted")


def test_full_chain_fictional(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("AOC_RECEIPTS", str(tmp_path / "r.jsonl"))
    from core.acquisition import (create_campaign, current_totals, funnel,
                                  ingest_observation, link_creative,
                                  record_conversion, record_lead,
                                  record_qualification)
    from core.review import sign_off
    r = _build(tmp_path)
    cid = r["plan"]["content_id"]
    out = Path(r["out_dir"])
    sign_off(tmp_path / "r.jsonl", cid, "approved", "test", reviewer="tester",
             store_dir=tmp_path / "store")
    create_campaign("test-camp-3", "nails", "muse-quickstart", 1,
                    hypothesis="test", budget_gbp=0)
    link = link_creative("test-camp-3", cid)
    assert link["creative_id"].startswith("CRT:")
    url = "https://www.tiktok.com/@FICTIONAL/video/1"
    for obs_time, views in [("2026-09-24T10:00:00", 100),
                            ("2026-09-25T10:00:00", 150)]:
        assert ingest_observation("FICTIONAL-P1", obs_time, "views", views,
                                  "manual", "imp-t")
    # reimport is a no-op (idempotent)
    assert not ingest_observation("FICTIONAL-P1", "2026-09-25T10:00:00",
                                  "views", 150, "manual", "imp-t")
    assert current_totals("FICTIONAL-P1") == {"views": 150.0}
    record_lead("FICTIONAL-L1", source="tiktok-organic", campaign_id="test-camp-3",
                creative_id=link["creative_id"], permission_status="consented",
                permission_ref="FICTIONAL-dm-1")
    record_qualification("FICTIONAL-L1", True, is_owner_manager=True,
                         business_type="salon", stated_need="booking")
    record_conversion("FICTIONAL-L1", amount_gbp=20.0, paid_at="2026-09-26T10:00:00")
    f = funnel("test-camp-3")
    assert (f["leads"], f["qualified"], f["paid"], f["revenue_gbp"]) == (1, 1, 1, 20.0)
    _ = out  # silence linters
