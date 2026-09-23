"""Review + analytics tests: checklist runs, sign-off records, snapshots derive."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analytics import compile_learnings, derive, import_studio_csv, record_snapshot  # noqa: E402
from core.carousel import run_carousel  # noqa: E402
from core.review import run_review, sign_off  # noqa: E402


def test_review_auto_half_passes_good_build(tmp_path):
    r = run_carousel("UK electricians — still doing quotes at 9pm?", "faq",
                     base_dir=tmp_path / "store", receipts_path=tmp_path / "r.jsonl",
                     segment="electrician")
    from pathlib import Path as _P
    out = _P(r["out_dir"])
    review = run_review(out, r["plan"], r["gates"], r["manifest"]["validation"])
    assert review["auto_passed"], review["automated"]
    assert len(review["pending_human"]) == 7  # taste stays human
    assert Path(review["contact_sheet"]).exists()


def test_signoff_requires_reason(tmp_path):
    rp = tmp_path / "r.jsonl"
    s = sign_off(rp, "abc", "approved", "hook names buyer, proof before CTA")
    assert s["data"]["decision"] == "approved"
    try:
        sign_off(rp, "abc", "approved", "")
    except ValueError:
        pass
    else:
        raise AssertionError("empty reason accepted")
    try:
        sign_off(rp, "abc", "maybe", "reason")
    except ValueError:
        pass
    else:
        raise AssertionError("bad decision accepted")


def test_derive_rates():
    d = derive({"views": 1000, "likes": 40, "comments": 10, "shares": 5,
                "saves": 30, "leads": 3, "sales": 1, "spend_gbp": 70})
    assert d["engagement_rate"] == 5.5
    assert d["save_rate"] == 3.0  # completion proxy
    assert d["cpqc"] == round(70 / 3, 2)
    assert d["cpsc"] == 70.0


def test_derive_zero_views_safe():
    d = derive({})
    assert d["engagement_rate"] == 0.0
    assert d["cpqc"] is None and d["cpsc"] is None


def test_snapshots_append_never_overwrite(tmp_path):
    sp = tmp_path / "metrics.jsonl"
    record_snapshot(sp, "https://tiktok.com/@x/video/1", metrics={"views": 100})
    record_snapshot(sp, "https://tiktok.com/@x/video/1", metrics={"views": 150})
    lines = [ln for ln in open(sp) if ln.strip()]
    assert len(lines) == 2  # history preserved


def test_studio_csv_import(tmp_path):
    csvp = tmp_path / "studio.csv"
    csvp.write_text("post_url,content_id,views,likes,comments,shares,saves\n"
                    "https://tiktok.com/@x/video/1,aoc_abc,1000,40,10,5,30\n")
    n = import_studio_csv(csvp, tmp_path / "metrics.jsonl")
    assert n == 1


def test_compile_learnings_prefers_leads(tmp_path):
    sp = tmp_path / "metrics.jsonl"
    record_snapshot(sp, "url-a", metrics={"views": 50000, "leads": 0})
    record_snapshot(sp, "url-b", metrics={"views": 400, "leads": 4, "sales": 1, "spend_gbp": 70})
    out = compile_learnings(sp, tmp_path / "memory.json")
    assert out["snapshots"] == 2
    assert out["ranked"][0]["derived"]["cpqc"] == 70 / 4
