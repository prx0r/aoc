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


class TestChannels:
    def test_unknown_channel_raises_at_plan(self):
        from core.carousel import plan
        try:
            plan("hook", "opportunity", segment="nails", channel="myspace")
        except ValueError as e:
            assert "unknown channel" in str(e)
        else:
            raise AssertionError("unknown channel accepted")

    def test_channel_profiles_load(self):
        from core.channels import CHANNELS, load_channel
        for c in CHANNELS:
            assert load_channel(c)["channel"] == c

    def test_hashtags_merge_segment_first(self):
        from core.channels import channel_hashtags
        tags = channel_hashtags("tiktok", ["#nailtech", "#smallbusiness"])
        assert tags.count("#smallbusiness") == 1
        assert "#nailtech" in tags

    def test_publish_packet_carries_channel(self, tmp_path):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.carousel import run_carousel
        r = run_carousel("Nail techs — DMs at midnight, booking at 9am?",
                         "opportunity", base_dir=tmp_path / "store",
                         receipts_path=tmp_path / "r.jsonl",
                         segment="nails", channel="facebook")
        assert r["plan"]["channel"] == "facebook"


class TestIdentityChain:
    def test_resolver_rejects_empty_id(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from mcp_server import _resolve_build
        try:
            _resolve_build("")
        except ValueError as e:
            assert "required" in str(e)
        else:
            raise AssertionError("empty content_id resolved")
        try:
            _resolve_build(None)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("None content_id resolved")

    def test_same_hook_prefix_builds_stay_distinct(self, tmp_path):
        from core.carousel import run_carousel
        a = run_carousel("Cleaners test hook alpha?", "opportunity",
                         base_dir=tmp_path / "store",
                         receipts_path=tmp_path / "r.jsonl", segment="cleaners")
        b = run_carousel("Cleaners test hook beta?", "opportunity",
                         base_dir=tmp_path / "store",
                         receipts_path=tmp_path / "r.jsonl", segment="cleaners")
        assert a["plan"]["content_id"] != b["plan"]["content_id"]
        assert a["out_dir"] != b["out_dir"]


class TestChannelHashtags:
    def test_segment_tags_lead(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.channels import channel_hashtags
        tags = channel_hashtags("tiktok", ["#nailtech", "#smallbusiness"])
        assert tags[0] == "#nailtech"
        assert "#electrician" in tags  # channel suggestions still present
        assert len(tags) == len(set(tags))


class TestPremiumRenderer:
    def test_cta_slide_validates_bright_band(self, tmp_path):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from render.slide import render_slide, _accent_for
        from core.validate import validate_slide
        p = render_slide("DM TEST for £20 setup.", None, tmp_path / "cta.jpg",
                         kind="close", accent=_accent_for("nails"),
                         slide_index=5, slide_total=6)
        v = validate_slide(p)
        assert v["ok"], v
        assert v["checks"]["backdrop"]["ok"]

    def test_renderer_deterministic(self, tmp_path):
        import sys as _sys, hashlib as _hl
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from render.slide import render_slide, _accent_for
        kw = dict(kind="body", accent=_accent_for("nails"), slide_index=1, slide_total=6)
        a = render_slide("Determinism check one two three.", None, tmp_path / "a.jpg", **kw)
        b = render_slide("Determinism check one two three.", None, tmp_path / "b.jpg", **kw)
        assert _hl.sha256(a.read_bytes()).hexdigest() == _hl.sha256(b.read_bytes()).hexdigest()

    def test_accents_stable_per_segment(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from render.slide import _accent_for
        assert _accent_for("nails") == _accent_for("nails")


class TestPhotoBackgrounds:
    def test_photo_for_local_only(self, tmp_path):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.images import photo_for, credit_line
        p = photo_for("electrician", 0)
        assert p.exists()
        assert photo_for("plumber", 0) is None  # unmapped → gradient
        assert "Wikimedia Commons" in credit_line("electrician", 6)
        assert credit_line("gardeners", 6) == ""  # CC0 only

    def test_photo_deck_validates(self, tmp_path):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.carousel import run_carousel
        r = run_carousel("More customers or fewer skips — which grows your round?",
                         "opportunity", base_dir=tmp_path / "store",
                         receipts_path=tmp_path / "r.jsonl",
                         segment="gardeners", photos=True)
        assert r["manifest"]["validation"]["passed"]
        assert "photo_credit" in r["manifest"]

    def test_generate_seam_blocked(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.images import generate
        try:
            generate("a glimling", "x.jpg")
        except NotImplementedError as e:
            assert "CLOUDFLARE_API_TOKEN" in str(e)
        else:
            raise AssertionError("generate() should be blocked without a live token")
