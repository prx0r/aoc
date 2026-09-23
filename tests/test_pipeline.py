"""End-to-end pipeline test: plan → render → zip → receipt. No network."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.carousel import export, plan, render  # noqa: E402
from core.memory import rank, record  # noqa: E402
from core.receipt import verify_chain  # noqa: E402
from core.state import ContentStatus, check_transition, create_content, transition  # noqa: E402


def test_state_machine_forces_review():
    assert check_transition(ContentStatus.IDEA, ContentStatus.DRAFT)
    assert not check_transition(ContentStatus.IDEA, ContentStatus.PUBLISHED)
    assert not check_transition(ContentStatus.DRAFT, ContentStatus.PUBLISHED)
    c = create_content("x", "hook", [], "opportunity")
    c = transition(c, ContentStatus.DRAFT)
    c = transition(c, ContentStatus.IN_REVIEW)
    c = transition(c, ContentStatus.APPROVED)
    assert c["status"] == "approved"


def test_carousel_builds_pngs_and_zip(tmp_path):
    p = plan("UK electricians — still doing quotes at 9pm?", "opportunity")
    assert len(p["slides"]) >= 5
    m = render(p, tmp_path / "out")
    assert len(m["slides"]) >= 5
    for name in m["slides"]:
        fp = tmp_path / "out" / name
        assert fp.exists()
        with open(fp, "rb") as f:
            assert f.read(2) == b"\xff\xd8"  # JPEG magic
    z = export(m, tmp_path / "out")
    assert z.exists() and z.stat().st_size > 1000


def test_memory_prefers_leads(tmp_path):
    mem = tmp_path / "memory.json"
    record(mem, {"audience": "e", "hook": "A", "angle": "q", "slide_count": 6, "cta": "DM", "visual_style": "dark"}, {"views": 10000, "leads": 0, "spend_gbp": 0})
    record(mem, {"audience": "e", "hook": "B", "angle": "q", "slide_count": 6, "cta": "DM", "visual_style": "dark"}, {"views": 100, "leads": 3, "spend_gbp": 30})
    ranked = rank(mem, "leads")
    assert ranked[0][1]["totals"]["leads"] == 3


def test_receipt_chain(tmp_path):
    from core.receipt import append_receipt
    rp = tmp_path / "r.jsonl"
    append_receipt(rp, "built", {"a": 1})
    append_receipt(rp, "built", {"a": 2})
    ok, _ = verify_chain(rp)
    assert ok


def test_segments_are_skins():
    from slides.generate import SEGMENT_IDS, get_hooks, generate_slides_deterministic, load_segment
    assert len(SEGMENT_IDS) == 14
    closes = {"electrician": "QUOTE", "beautician": "BOOKING", "plumber": "JOBS",
              "sole_trader": "SETUP", "nails": "NAILS", "lashes": "LASHES",
              "hair": "HAIR", "cleaners": "CLEAN", "dog_groomers": "GROOM",
              "gardeners": "ROUND", "car_detailers": "DETAIL",
              "driving_instructors": "LESSONS", "weddings": "WEDDING",
              "powthings": "GOBLIN"}
    for seg in SEGMENT_IDS:
        skin = load_segment(seg)
        assert skin["profile"]["id"] == seg
        assert len(get_hooks(seg)) >= 6
        for template in ("opportunity", "faq", "comparison"):
            s = generate_slides_deterministic("test hook", seg, template)
            assert closes[seg] in s.slides[-1].text, (seg, template)
            # no cross-contamination: non-electrician decks never mention Tradify
            if seg != "electrician":
                assert not any("Tradify" in x.text for x in s.slides), (seg, template)
