"""Per-business personalization tests: identity-only, consent-gated, scored.

Compliance properties (from aionboard OFFER.md + targets.md):
- business identity comes from CSV columns, never invented
- no personalized numbers/claims/outcomes
- research-only by default; consented only for 1-to-1 follow-up
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.carousel import run_variant  # noqa: E402
from core.gates import gate_personalization  # noqa: E402
from core.personalize import (  # noqa: E402
    personalize_hook,
    score_prospect,
    short_name,
    top_prospects,
    variant_spec,
)

ROW = {"company_number": "12013809", "name": "GALLOWAY GROUP LTD.",
       "postcode": "G2 1DY", "region": "G2", "sic_codes": "25990,43210,43999",
       "status": "active", "cluster": "electrical"}


def test_short_name_strips_suffix():
    assert short_name("GALLOWAY GROUP LTD.") == "GALLOWAY GROUP"
    assert len(short_name("A" * 40)) <= 26


def test_personalize_hook_identity_only():
    hook = personalize_hook("still doing quotes at 9pm?", ROW)
    assert "GALLOWAY GROUP" in hook
    assert "G2" in hook
    assert "£" not in hook and "%" not in hook  # no numbers invented


def test_variant_defaults_research_only():
    v = variant_spec(ROW, "still doing quotes at 9pm?", "opportunity", "electrician")
    assert v["status"] == "research-only"
    assert v["company_number"] == "12013809"
    ok, _ = gate_personalization(v)
    assert ok


def test_variant_refuses_missing_identity():
    v = variant_spec({"name": "", "company_number": "", "region": "",
                      "sic_codes": "", "status": "active"},
                     "hook", "opportunity", "electrician")
    ok, detail = gate_personalization(v)
    assert not ok and "identity" in detail


def test_variant_refuses_forbidden_tokens():
    v = variant_spec(ROW, "hook", "opportunity", "electrician")
    v["hook"] = "Hi {first_name}, you lose {amount}/month"
    ok, detail = gate_personalization(v)
    assert not ok and "forbidden tokens" in detail


def test_scoring_uses_csv_fields_only():
    counts = {"G2": 120}
    s = score_prospect(ROW, counts)
    assert s["score"] == 15 + 20 + 5  # density + diversity + construction SIC
    assert s["age_unknown"] is True  # honest: no CH API, no age points


def test_top_prospects_from_real_csv():
    top = top_prospects("/root/aionboard/prospects_electrical.csv", limit=5)
    assert len(top) == 5
    assert all(t["score"] >= 25 for t in top)
    assert all(t.get("company_number") for t in top)


def test_variant_build_end_to_end(tmp_path):
    v = variant_spec(ROW, "still doing quotes at 9pm?", "opportunity",
                     "electrician", status="research-only")
    r = run_variant(v, base_dir=tmp_path / "store", receipts_path=tmp_path / "r.jsonl")
    assert Path(r["zip"]).exists()
    assert r["receipt"]["data"]["variant"]["status"] == "research-only"
    assert r["receipt"]["data"]["variant"]["business"] == "GALLOWAY GROUP"
    assert "GALLOWAY GROUP" in r["plan"]["slides"][0]["text"]
