"""Validation tests: gates catch bad carousels BEFORE render.

Mirrors /content's gate tests: evidence-fresh, no-duplicate, claim-resolved,
plus hook-quality and render-legible. Fail-closed with FAIL receipts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.carousel import plan, run_carousel  # noqa: E402
from core.gates import run_gates  # noqa: E402
from core.proof import proof_from_plan  # noqa: E402
from core.validate import contact_sheet, validate_slide  # noqa: E402
from slides.generate import load_segment  # noqa: E402


def test_hook_quality_rejects_vague_product_hook():
    from core.gates import gate_hook_quality
    ok, _ = gate_hook_quality("AI can transform your business today", "electrician")
    assert not ok  # names no buyer, no number, no question
    ok, _ = gate_hook_quality("UK electricians — still doing quotes at 9pm?", "electrician")
    assert ok


def test_hook_quality_rejects_long_hook():
    from core.gates import gate_hook_quality
    ok, detail = gate_hook_quality(
        "This is a very long hook with far too many words in it for TikTok", "electrician")
    assert not ok and "too long" in detail


def test_proof_refuses_untraced_stat():
    skin = load_segment("electrician")
    bad_plan = {"content_id": "x", "hook": "hook", "template": "opportunity",
                "segment": "electrician", "created_at": "now",
                "slides": [{"text": "hook", "kind": "hook"},
                           {"text": "We saved clients 99% overnight guaranteed", "kind": "body"}]}
    try:
        proof_from_plan(bad_plan, skin)
    except ValueError as e:
        assert "traces to nothing" in str(e)
    else:
        raise AssertionError("untraced stat was not refused")


def test_gates_reject_duplicate(tmp_path):
    p = plan("UK electricians — still doing quotes at 9pm?", "opportunity", segment="electrician")
    skin = load_segment("electrician")
    proof = proof_from_plan(p, skin)
    rp = tmp_path / "r.jsonl"
    g1 = run_gates(p, proof, "electrician", rp)
    assert g1["passed"], g1
    r = run_carousel("UK electricians — still doing quotes at 9pm?", "opportunity",
                     base_dir=tmp_path / "store", receipts_path=rp, segment="electrician")
    assert Path(r["zip"]).exists()
    g2 = run_gates(p, proof, "electrician", rp)
    assert not g2["passed"]
    assert not g2["gates"]["no-duplicate-v1"]["ok"]


def test_gate_failure_writes_fail_receipt(tmp_path):
    import json as _json
    rp = tmp_path / "r.jsonl"
    try:
        run_carousel("AI can transform your business today", "opportunity",
                     base_dir=tmp_path / "store", receipts_path=rp, segment="electrician")
    except ValueError:
        pass
    else:
        raise AssertionError("bad hook rendered anyway")
    events = [_json.loads(ln)["event"] for ln in open(rp) if ln.strip()]
    assert "carousel_rejected" in events
    assert not any(e == "carousel_built" for e in events)


def test_pixel_validation_and_contact_sheet(tmp_path):
    r = run_carousel("UK electricians — still doing quotes at 9pm?", "before_after",
                     base_dir=tmp_path / "store", receipts_path=tmp_path / "r.jsonl",
                     segment="electrician")
    out = tmp_path / "store" / r["plan"]["content_id"]
    first = out / r["manifest"]["slides"][0]
    v = validate_slide(first)
    assert v["ok"], v
    assert v["checks"]["dims"]["ok"]
    assert v["checks"]["backdrop"]["ok"]
    assert v["checks"]["text_present"]["ok"]
    sheet = contact_sheet(out)
    assert sheet.exists() and sheet.stat().st_size > 1000
