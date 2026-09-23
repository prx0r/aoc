"""Port tests: ographuk invariants adapted to aoc.

Class-per-invariant, mirroring ographuk/tests/test_contracts.py structure:
tamper, idempotence, parity, fail-closed boundaries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fetch import FetchStatus, fetch_failed, fetch_ok  # noqa: E402
from core.ids import canonical, content_id_for, entity_id, record_id  # noqa: E402
from core.proof import proof_from_plan  # noqa: E402
from core.schema_manifest import SCHEMAS, check_parity  # noqa: E402
from slides.generate import load_segment  # noqa: E402


class TestCanonicalIds:
    def test_rejects_nan(self):
        try:
            canonical({"v": float("nan")})
        except ValueError:
            pass
        else:
            raise AssertionError("NaN accepted in ID payload")

    def test_rejects_inf_nested(self):
        try:
            canonical({"a": [1, {"b": float("inf")}]})
        except ValueError:
            pass
        else:
            raise AssertionError("Inf accepted in ID payload")

    def test_none_passes(self):
        canonical({"v": None})

    def test_entity_survives_rename(self):
        a = entity_id("business", "companies-house", "12345")
        assert entity_id("business", "companies-house", "12345") == a
        assert entity_id("business", "companies-house", "12346") != a

    def test_record_ids_full_length(self):
        rid = record_id("PROOF", {"x": 1})
        assert rid.startswith("PROOF:")
        assert len(rid.split(":")[1]) == 64

    def test_content_id_includes_segment(self):
        # The old sha256(hook|template)[:12] collided across segments.
        a = content_id_for("same hook", "opportunity", "electrician", "skinA")
        b = content_id_for("same hook", "opportunity", "lashes", "skinA")
        c = content_id_for("same hook", "opportunity", "electrician", "skinB")
        assert a != b and a != c


class TestSchemaParity:
    def test_live_records_match_manifest(self, tmp_path):
        import json
        from core.carousel import run_carousel
        from core.state import create_content
        r = run_carousel("UK electricians — still doing quotes at 9pm?", "faq",
                         base_dir=tmp_path / "store", receipts_path=tmp_path / "r.jsonl",
                         segment="electrician")
        import json as _json
        content = create_content("x", "hook", [], "opportunity")
        live_receipt = _json.loads((tmp_path / "r.jsonl").read_text().splitlines()[-1])
        manifest = {k: v for k, v in r["manifest"].items()
                    if k in SCHEMAS["Manifest"]}
        result = check_parity({
            "Content": content,
            "Plan": {k: v for k, v in r["plan"].items()
                     if k in SCHEMAS["Plan"]},
            "Proof": r["proof"],
            "Manifest": manifest,
            "Receipt": live_receipt,
            "Gates": r["gates"],
            "Snapshot": {"at": "t", "post_url": "u", "content_id": "c",
                         "source": "s", "metrics": {}},
            "Variant": {"business": "b", "company_number": "n", "area": "a",
                        "segment": "s", "template": "t", "hook": "h",
                        "score": {}, "status": "research-only", "source": "s"},
        })
        assert result["missing"] == {}, result


class TestFetchSemantics:
    def test_missing_csv_is_failed_not_empty(self):
        from core.personalize import load_prospects_result
        r = load_prospects_result("/nonexistent/prospects.csv")
        assert r.status == FetchStatus.FAILED
        assert not r.is_success
        assert not r.complete  # outage is UNKNOWN

    def test_empty_csv_is_success_empty(self, tmp_path):
        from core.personalize import load_prospects_result
        fp = tmp_path / "empty.csv"
        fp.write_text("company_number,name,postcode,region,sic_codes,status,cluster\n")
        r = load_prospects_result(fp)
        assert r.status == FetchStatus.SUCCESS_EMPTY
        assert r.is_success and not r.has_data

    def test_partial_cannot_claim_complete(self):
        from core.fetch import FetchResult
        try:
            FetchResult(FetchStatus.PARTIAL, data=[1], complete=True)
        except ValueError:
            pass
        else:
            raise AssertionError("PARTIAL+complete accepted")

    def test_fetch_ok_helpers(self):
        assert fetch_ok([1]).is_success and fetch_ok([1]).has_data
        assert fetch_ok([]).status == FetchStatus.SUCCESS_EMPTY
        assert not fetch_failed("x").is_success


class TestProofBoundary:
    def test_rejects_injected_claims(self):
        # Mirrors ographuk TestSeesawRejectsUnbackedFeatures: caller-supplied
        # numbers must never appear in the proof.
        skin = load_segment("electrician")
        plan = {"content_id": "x", "hook": "hook", "template": "opportunity",
                "segment": "electrician", "created_at": "now",
                "demand_change": 0.99,  # injected junk, like seesaw features
                "slides": [{"text": "hook", "kind": "hook"},
                           {"text": "Demand up 99% this week", "kind": "body"}]}
        try:
            proof_from_plan(plan, skin)
        except ValueError as e:
            assert "traces to nothing" in str(e)
        else:
            raise AssertionError("injected 99% claim survived")

    def test_proof_ids_are_typed_full_hash(self):
        skin = load_segment("electrician")
        plan = {"content_id": "x", "hook": "hook", "template": "opportunity",
                "segment": "electrician", "created_at": "now",
                "slides": [{"text": "hook", "kind": "hook"}]}
        proof = proof_from_plan(plan, skin)
        assert proof.proof_id.startswith("PROOF:")
        assert len(proof.proof_id.split(":")[1]) == 64  # no SHA1, no truncation

    def test_lineage_replay(self):
        skin = load_segment("electrician")
        mk = lambda: {"content_id": "x", "hook": "hook", "template": "opportunity",
                      "segment": "electrician", "created_at": "now",
                      "skin_hash": "abc",
                      "slides": [{"text": "hook", "kind": "hook"}]}
        a = proof_from_plan(mk(), skin)
        b = proof_from_plan(mk(), skin)
        assert a.lineage_root == b.lineage_root  # same skin+plan = same root

    def test_evidence_refs_are_locators(self):
        from core.carousel import plan as make_plan
        p = make_plan("Salon owners — how much did no-shows cost you last month?",
                      "opportunity", segment="beautician")
        skin = load_segment("beautician")
        proof = proof_from_plan(p, skin)
        assert proof.evidence_refs, "expected at least one traced ref"
        assert all(r.startswith("segments/beautician/proofs.yaml#/proofs/") for r in proof.evidence_refs), proof.evidence_refs


class TestSkinHygiene:
    def test_all_skin_yaml_parses(self):
        import yaml
        from pathlib import Path as _P
        bad = []
        for fp in sorted(_P("segments").rglob("*.yaml")):
            try:
                yaml.safe_load(fp.read_text())
            except Exception as e:
                bad.append((str(fp), str(e)[:60]))
        assert not bad, bad

    def test_no_near_duplicate_slides_in_any_deck(self):
        import re
        from slides.generate import SEGMENT_IDS, generate_slides_deterministic
        templates = ["opportunity", "before_after", "faq", "social_proof",
                     "demo", "diagnostic", "teardown", "comparison",
                     "annuity", "retention", "waitlist"]

        def overlap(a, b):
            stop = {"the", "a", "an", "to", "of", "and", "or"}
            wa = set(re.findall(r"[a-z0-9]+", a.lower())) - stop
            wb = set(re.findall(r"[a-z0-9]+", b.lower())) - stop
            return len(wa & wb) / len(wa | wb) if wa and wb else 0.0

        bad = []
        unbuildable = []
        for seg in SEGMENT_IDS:
            for t in templates:
                try:
                    s = generate_slides_deterministic("test hook", seg, t)
                except ValueError as e:
                    # every segment × template must build — a collapse means
                    # skin proofs restate pains (fix the skin, not the test)
                    unbuildable.append((seg, t, str(e)[:60]))
                    continue
                texts = [x.text for x in s.slides]
                for i in range(len(texts)):
                    for j in range(i + 1, len(texts)):
                        if overlap(texts[i], texts[j]) > 0.6:
                            bad.append((seg, t, texts[i][:40], texts[j][:40]))
        assert not unbuildable, unbuildable
        assert not bad, bad


class TestWedgePricing:
    def test_wedges_close_at_20(self):
        from slides.generate import generate_slides_deterministic
        for seg, kw in [("nails", "NAILS"), ("lashes", "LASHES"), ("hair", "HAIR"),
                        ("cleaners", "CLEAN"), ("car_detailers", "DETAIL"),
                        ("gardeners", "ROUND")]:
            s = generate_slides_deterministic("test hook", seg, "opportunity")
            assert "£20" in s.slides[-1].text, (seg, s.slides[-1].text)
            assert kw in s.slides[-1].text, seg

    def test_electrician_stays_499_pow_route(self):
        from slides.generate import generate_slides_deterministic, load_segment
        s = generate_slides_deterministic("test hook", "electrician", "opportunity")
        assert "£499" in s.slides[-1].text
        note = load_segment("electrician").get("profile", {}).get("offer", {}).get("note", "")
        assert "£20" in note and "POW" in note.upper() or "higher-value" in note

    def test_waitlist_template_builds(self):
        from slides.generate import generate_slides_deterministic
        s = generate_slides_deterministic("Just downloaded Muse?", "nails", "waitlist")
        assert len(s.slides) == 6
        assert "UK list" in s.slides[-1].text
        assert "Sep 8" in s.slides[1].text


class TestBankHygiene:
    def test_all_bank_hooks_pass_gates(self):
        from core.gates import gate_hook_quality
        from slides.generate import SEGMENT_IDS, get_hooks
        bad = [(seg, h["text"][:60])
               for seg in SEGMENT_IDS for h in get_hooks(seg)
               if not gate_hook_quality(h["text"], seg)[0]]
        assert not bad, bad

    def test_all_skin_yaml_parses(self):
        import yaml
        from pathlib import Path as _P
        bad = []
        for fp in sorted(_P("segments").rglob("*.yaml")):
            try:
                yaml.safe_load(fp.read_text())
            except Exception as e:
                bad.append((str(fp), str(e)[:60]))
        assert not bad, bad
