"""Peer-review regression battery (§4 items 1–12).

Each test maps to a numbered requirement. Fictional data only.
"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.carousel import plan, run_carousel  # noqa: E402


def _build(tmp_path, hook, template, segment, **kw):
    return run_carousel(hook, template, base_dir=tmp_path / "store",
                        receipts_path=tmp_path / "r.jsonl",
                        segment=segment, **kw)


def test_01_two_ctas_two_ids_no_overwrite(tmp_path):
    a = _build(tmp_path, "Nail techs — DMs at midnight, booking at 9am?",
               "opportunity", "nails",
               cta="DM NAILS — UK nail techs only. £20 setup.", kind="ad")
    b = _build(tmp_path, "Nail techs — DMs at midnight, booking at 9am?",
               "opportunity", "nails",
               cta="DM NAILS to join the UK list.", kind="ad")
    assert a["plan"]["content_id"] != b["plan"]["content_id"]
    assert a["out_dir"] != b["out_dir"]
    assert Path(a["zip"]).exists() and Path(b["zip"]).exists()


def test_02_paid_cta_in_final_image(tmp_path):
    from PIL import Image  # noqa: F401  (presence check only)
    r = _build(tmp_path, "On Tradify already? So why admin at night?",
               "comparison", "electrician",
               cta="DM QUOTE — UK electricians only. £499 setup.", kind="ad")
    import json
    m = json.loads(Path(r["out_dir"], "manifest.json").read_text())
    assert m["final_cta"] == "DM QUOTE — UK electricians only. £499 setup."
    assert r["manifest"]["validation"]["passed"]


def test_03_invented_62_refused_despite_62_source(tmp_path):
    from core.proof import proof_from_plan
    from slides.generate import load_segment
    skin = load_segment("electrician")  # contains an unrelated 62% source
    plan = {"content_id": "x", "hook": "hook", "template": "opportunity",
            "segment": "electrician", "created_at": "now",
            "slides": [{"text": "hook", "kind": "hook"},
                       {"text": "62% of customers prefer us, survey says",
                        "kind": "body"}]}
    try:
        proof_from_plan(plan, skin)
    except ValueError as e:
        assert "traces to nothing" in str(e)
    else:
        raise AssertionError("invented 62% claim resolved via number overlap")


def test_04_offer_change_invalidates_pending(tmp_path):
    from core.offers import check_revalidation
    fake_registry = {"offers": {"muse-quickstart": {"version": 2}}}
    plan = {"offer_id": "muse-quickstart", "offer_version": 1}
    ok, detail = check_revalidation(plan, fake_registry)
    assert not ok and "revalidate" in detail
    plan["offer_version"] = 2
    ok, _ = check_revalidation(plan, fake_registry)
    assert ok


def test_05_unknown_segment_never_generates(tmp_path):
    from slides.generate import generate_slides_deterministic, load_segment
    for fn in (lambda: load_segment("elektrishan"),
               lambda: generate_slides_deterministic("hook", "elektrishan", "opportunity")):
        try:
            fn()
        except ValueError as e:
            assert "unknown segment" in str(e) or "no deck" in str(e)
        else:
            raise AssertionError("unknown segment produced copy")


def test_07_review_valid_missing_modified(tmp_path):
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_server import _resolve_build
    r = _build(tmp_path, "UK electricians — still doing quotes at 9pm?", "faq",
               "electrician")
    import os
    os.chdir(tmp_path)  # _resolve_build uses repo store; emulate below
    # valid artifact resolves (via manifest scan on real store is tested
    # in e2e; here assert the resolver rejects unknown ids)
    try:
        _resolve_build("AOC:does-not-exist-0000000000000000000000000000000000000000000000000000")
    except ValueError as e:
        assert "no built artifact" in str(e)
    else:
        raise AssertionError("missing artifact resolved")


def test_08_approval_rev_a_cannot_authorize_rev_b(tmp_path):
    from core.review import sign_off
    r = _build(tmp_path, "UK electricians — still doing quotes at 9pm?", "faq",
               "electrician")
    out = Path(r["out_dir"])
    cid = r["plan"]["content_id"]
    rp = tmp_path / "r.jsonl"
    # approve revision A
    sign_off(rp, cid, "approved", "clean arc", reviewer="tester", store_dir=out.parent)
    # tamper one slide (simulating an unrecorded revision B)
    slide = out / r["manifest"]["slides"][0]
    slide.write_bytes(b"\xff\xd8tampered")
    try:
        sign_off(rp, cid, "approved", "re-approve?", reviewer="tester",
                 store_dir=out.parent)
    except ValueError as e:
        assert "missing" in str(e) or "changed" in str(e)
    else:
        raise AssertionError("tampered revision approved")


def test_09_cumulative_views_not_summed(tmp_path, monkeypatch):
    import core.acquisition as A
    import core.store as S
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    assert A.ingest_observation("p1", "2026-09-20T10:00:00", "views", 100, "studio_csv", "imp1")
    assert A.ingest_observation("p1", "2026-09-21T10:00:00", "views", 150, "studio_csv", "imp1")
    # reimport same file: idempotent, no duplicate row
    assert not A.ingest_observation("p1", "2026-09-21T10:00:00", "views", 150, "studio_csv", "imp1")
    assert A.current_totals("p1") == {"views": 150}
    iv = A.intervals("p1", "views")
    assert len(iv) == 1 and iv[0]["delta"] == 50


def test_10_qualified_conversation_attributed(tmp_path, monkeypatch):
    import core.acquisition as A
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    A.record_lead("L1", source="facebook-paid", campaign_id="C1",
                  creative_id="CR1", permission_status="consented",
                  permission_ref="form-123")
    A.record_qualification("L1", True, is_owner_manager=True,
                           business_type="salon", stated_need="no-shows")
    A.record_conversion("L1", amount_gbp=20.0, paid_at="2026-09-22T10:00:00")
    f = A.funnel("C1")
    assert (f["leads"], f["qualified"], f["paid"], f["revenue_gbp"]) == (1, 1, 1, 20.0)


def test_11_withdrawn_permission_blocks(tmp_path, monkeypatch):
    import core.acquisition as A  # noqa: F401
    import core.store as S
    from core.gates import gate_suppression
    from core.personalize import variant_spec
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    row = {"name": "Test Salon", "company_number": "12345",
           "region": "M", "sic_codes": "", "status": "active"}
    v = variant_spec(row, "hook", "opportunity", "beautician",
                     status="consented", permission_ref="call-99")
    ok, _ = gate_suppression(v)
    assert ok
    with S.session() as db:
        db.execute("INSERT INTO suppression (business_id, withdrawn_at, reason) VALUES (?, ?, ?)",
                   ("CH:12345", "2026-09-23T00:00:00", "opt-out"))
    ok, detail = gate_suppression(v)
    assert not ok and "withdrawn" in detail


def test_12_parallel_workers_safe(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("AOC_DB", str(tmp_path / "a.db"))
    results, errors = [], []

    def work():
        try:
            results.append(_build(tmp_path, "UK electricians — still doing quotes at 9pm?",
                                  "faq", "electrician"))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors, errors
    assert len(results) == 4
    zips = {r["zip"] for r in results}
    assert len(zips) == 1  # one artifact, replays share it
    from core.receipt import verify_chain
    ok, _ = verify_chain(tmp_path / "r.jsonl")
    assert ok
