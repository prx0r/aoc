"""Carousel orchestrator — hook → slides → PNGs → ZIP → receipt.

Stolen structure: ClipFactory 3-step versioned pipeline + ai-ugc JSON-as-contract.
Each stage independently re-runnable. Nothing publishes. Human posts manually
so trending audio can be chosen inside TikTok.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import os

from core.gates import run_gates
from core.ids import content_id_for, record_id, record_short
from core.offers import get_offer, offer_for_segment
from core.proof import proof_from_plan
from core.receipt import append_receipt
from core.validate import contact_sheet, validate_carousel
from render.slide import export_zip, render_slideshow
from slides.generate import generate_slides_deterministic, load_segment, script_to_json, skin_hash


# Bump when render/slide.py changes: same hook+template must mint a new ID
# rather than collide with pixels rendered by older code.
RENDER_V = 3

RENDERER = "render.slide"


def _content_id(hook: str, template: str, segment: str = "electrician",
                kind: str = "organic", cta: str = "", caption: str = "",
                offer_id: str = "", offer_version: int = 0,
                skin: str = "") -> str:
    return content_id_for(hook, template, segment, skin or skin_hash(segment),
                          gen_v=RENDER_V, kind=kind, cta=cta,
                          caption=caption, offer_id=offer_id,
                          offer_version=offer_version)


def _experiment_id(segment: str, offer_id: str, offer_version: int,
                   template: str, channel: str) -> str:
    """Stable test identity: audience + offer + hypothesis + channel."""
    return record_id("EXP", {"segment": segment, "offer_id": offer_id,
                             "offer_version": offer_version,
                             "template": template, "channel": channel})


def plan(hook: str, template: str = "opportunity", audience: str = "electrician",
         slide_count: int = 6, cta: str | None = None, segment: str | None = None,
         kind: str = "organic", caption: str = "",
         channel: str = "tiktok") -> dict:
    """Stage 1: hook → slide script (JSON contract). No files, no LLM needed.

    audience/segment select the skin (default electrician). CTA defaults to
    the segment close line unless explicitly passed. kind="ad" marks paid
    variants — recorded on the plan so IDs never collide with organic.

    Identity model (review workstream B):
    - experiment_id: stable test (segment + offer + template + channel)
    - content_id: immutable creative revision (hook + final CTA + caption +
      skin + renderer + offer version). Two CTAs = two IDs, always.
    """
    seg = segment or audience
    from slides.generate import segment_close
    cta = cta or segment_close(seg)
    offer_id, offer = offer_for_segment(seg)
    script = generate_slides_deterministic(hook, seg, template, slide_count)
    d = script_to_json(script)
    d["cta"] = cta
    d["caption"] = caption
    d["segment"] = seg
    d["kind"] = kind
    d["channel"] = channel
    d["skin_hash"] = skin_hash(seg)
    d["offer_id"] = offer_id
    d["offer_version"] = offer["version"]
    d["experiment_id"] = _experiment_id(seg, offer_id, offer["version"],
                                        template, channel)
    d["content_id"] = _content_id(hook, template, seg, kind=kind, cta=cta,
                                  caption=caption, offer_id=offer_id,
                                  offer_version=offer["version"],
                                  skin=d["skin_hash"])
    d["created_at"] = datetime.now(timezone.utc).isoformat()
    return d


def _final_slides(plan_dict: dict) -> list[dict]:
    """Resolve the exact final slide list, including the CTA.

    Organic: the deck's own close stands (waitlist/demo carry theirs);
    the segment CTA appends only when no DM close exists.
    Ads (kind=ad): the requested CTA REPLACES the deck close verbatim —
    never inferred, never dropped. This fixes the paid-CTA defect where
    any "DM " text suppressed the mandatory qualification line.
    """
    slides = [dict(s) for s in plan_dict["slides"]]
    cta = plan_dict.get("cta", "")
    if plan_dict.get("kind") == "ad":
        if slides and slides[-1].get("kind") == "close":
            slides[-1] = {"text": cta, "position": 0.5, "kind": "close", "tags": []}
        elif cta:
            slides.append({"text": cta, "position": 0.5, "kind": "close", "tags": []})
        return slides
    last = slides[-1].get("text", "") if slides else ""
    has_cta = (cta and cta in last) or "DM " in last
    if cta and not has_cta:
        slides.append({"text": cta, "position": 0.5, "kind": "close", "tags": []})
    return slides


def render(plan_dict: dict, out_dir: Path | str, font_path: str | None = None) -> dict:
    """Stage 2: script → 1080x1920 PNGs."""
    out_dir = Path(out_dir)
    slides = _final_slides(plan_dict)
    paths = render_slideshow(slides, out_dir, font_path=font_path)
    manifest = {
        "content_id": plan_dict["content_id"],
        "experiment_id": plan_dict.get("experiment_id", ""),
        "hook": plan_dict["hook"],
        "template": plan_dict["template"],
        "kind": plan_dict.get("kind", "organic"),
        "final_cta": slides[-1].get("text", "") if slides else "",
        "slides": [p.name for p in paths],
        "sha256": {},
    }
    import hashlib as _hl
    for p in paths:
        manifest["sha256"][p.name] = _hl.sha256(p.read_bytes()).hexdigest()
    (out_dir / "script.json").write_text(json.dumps(plan_dict, indent=2))
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def export(manifest: dict, out_dir: Path | str, zip_name: str = "tiktok_carousel.zip") -> Path:
    """Stage 3: PNGs → ZIP for manual TikTok upload."""
    out_dir = Path(out_dir)
    slides = [out_dir / n for n in manifest["slides"]]
    # verify hashes before export (ai-ugc pattern: refuse corrupt)
    for s in slides:
        expect = manifest["sha256"][s.name]
        got = __import__("hashlib").sha256(s.read_bytes()).hexdigest()
        if got != expect:
            raise ValueError(f"hash mismatch {s.name}: manifest corrupt")
    return export_zip(slides, out_dir / zip_name)


def _try_replay(out_dir: Path, plan_dict: dict, receipts_path: Path | str) -> dict | None:
    """Duplicate request for an existing creative: verify hashes and return
    the existing artifact WITHOUT rebuilding. A replay is recorded as such —
    distinct from a genuinely new revision (which would mint a new ID)."""
    import hashlib as _hl
    manifest_fp = out_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_fp.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("content_id") != plan_dict["content_id"]:
        return None  # same dir, different creative — should not happen; rebuild
    for name, expect in (manifest.get("sha256") or {}).items():
        fp = out_dir / name
        if not fp.exists() or _hl.sha256(fp.read_bytes()).hexdigest() != expect:
            return None  # corrupt — fall through to rebuild
    zip_path = out_dir / "tiktok_carousel.zip"
    receipt = append_receipt(receipts_path, "carousel_replayed", {
        "content_id": plan_dict["content_id"],
        "experiment_id": plan_dict.get("experiment_id", ""),
        "zip": str(zip_path),
    })
    manifest["replayed"] = True
    return {"plan": plan_dict, "manifest": manifest,
            "zip": str(zip_path), "receipt": receipt,
            "out_dir": str(out_dir), "replayed": True}


def run_carousel(hook: str, template: str = "opportunity", base_dir: Path | str = "store",
                 receipts_path: Path | str = "receipts/content.jsonl",
                 segment: str = "electrician", audience: str | None = None,
                 enforce_gates: bool = True, variant: dict | None = None,
                 cta: str | None = None, kind: str = "organic") -> dict:
    """Full local run: plan → proof → gates → render → validate → export → receipt.

    Fail-closed like /content: gate failures write a FAIL receipt and raise;
    nothing renders. Pixel validation runs post-render; failures also FAIL.
    variant (optional): per-business spec from core.personalize — adds the
    personalization gate and stamps the receipt. No network. No publish.

    kind="ad": paid variant. Requires explicit cta with qualification
    (e.g. "UK electricians only"). Recorded on the receipt for spend tracking.
    """
    base = Path(base_dir)
    seg = segment or (audience or "electrician")
    if kind == "ad":
        if not cta:
            raise ValueError("ads require an explicit CTA with qualification")
        plan_dict = plan(hook, template, audience=seg, segment=seg, cta=cta, kind=kind)
    else:
        plan_dict = plan(hook, template, audience=seg, segment=seg)
    skin = load_segment(seg)
    # NOTE: plan_dict["content_id"] is the full AOC:<64hex> identity.
    # Filesystem dirs use the short display form (colons break Win/Mac/URLs).

    # proof + gates BEFORE render
    proof = proof_from_plan(plan_dict, skin)
    gates = run_gates(plan_dict, proof, seg, receipts_path, variant=variant)
    from core.store import session as _session, set_status as _set, upsert_content as _upsert
    with _session() as _db:
        _upsert(_db, plan_dict["content_id"], plan_dict.get("experiment_id", ""),
                seg, template, kind)
    if enforce_gates and not gates["passed"]:
        failed = {k: v for k, v in gates["gates"].items() if not v["ok"]}
        append_receipt(receipts_path, "carousel_rejected", {
            "content_id": plan_dict["content_id"],
            "hook": hook,
            "template": template,
            "segment": seg,
            "failed_gates": failed,
        })
        raise ValueError(f"gates failed: {failed}")
    with _session() as _db:
        _set(_db, plan_dict["content_id"], "validated")

    from core.ids import record_id, record_short
    # Storage path derives from the EXACT creative ID (hook+CTA+caption
    # included) — two CTAs never share a directory, fixing the ad/organic
    # collision where different creatives overwrote each other.
    out_dir = base / record_short("AOC", {"id": plan_dict["content_id"]})
    if out_dir.exists():
        existing = _try_replay(out_dir, plan_dict, receipts_path)
        if existing is not None:
            return existing
    # Atomic writes: render into a temp sibling, rename only on success.
    # Failed builds never overwrite (or leave half-written) valid outputs.
    import tempfile
    base.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=".build-", dir=str(base)))
    try:
        manifest = render(plan_dict, tmp_dir)
    except Exception:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    import shutil
    try:
        os.replace(tmp_dir, out_dir)
    except OSError:
        # Parallel worker lost the rename race: another thread built the
        # identical creative first. Verify it matches, share it, clean up.
        shutil.rmtree(tmp_dir, ignore_errors=True)
        replayed = _try_replay(out_dir, plan_dict, receipts_path)
        if replayed is None:
            raise ValueError("rename race lost and winner output invalid")
        replayed["out_dir"] = str(out_dir)
        return replayed

    # pixel validation AFTER render, before export
    validation = validate_carousel(out_dir, manifest)
    sheet = contact_sheet(out_dir)
    from core.review import run_review
    review = run_review(out_dir, plan_dict, gates, validation)
    manifest["validation"] = validation
    manifest["contact_sheet"] = sheet.name
    manifest["review"] = {"auto_passed": review["auto_passed"],
                          "pending_human": review["pending_human"]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if enforce_gates and not validation["passed"]:
        bad = {k: v for k, v in validation["slides"].items() if not v["ok"]}
        append_receipt(receipts_path, "carousel_rejected", {
            "content_id": plan_dict["content_id"],
            "reason": "pixel validation",
            "failed_slides": bad,
        })
        raise ValueError(f"pixel validation failed: {list(bad)}")

    with _session() as _db:
        _set(_db, plan_dict["content_id"], "rendered")
    zip_path = export(manifest, out_dir)
    import hashlib as _hl2
    receipt_data = {
        "content_id": plan_dict["content_id"],
        "experiment_id": plan_dict.get("experiment_id", ""),
        "asset_id": plan_dict["content_id"] + ":sha256:" + _hl2.sha256(
            zip_path.read_bytes()).hexdigest()[:16],
        "hook": hook,
        "template": template,
        "segment": seg,
        "kind": kind,
        "caption": plan_dict.get("caption", ""),
        "slides": len(manifest["slides"]),
        "gates": gates["gates"],
        "proof_id": proof.proof_id,
        "zip": str(zip_path),
    }
    if variant is not None:
        receipt_data["variant"] = {
            "business": variant.get("business"),
            "company_number": variant.get("company_number"),
            "area": variant.get("area"),
            "status": variant.get("status"),
            "score": (variant.get("score") or {}).get("score"),
        }
    receipt = append_receipt(receipts_path, "carousel_built", receipt_data)
    with _session() as _db:
        _set(_db, plan_dict["content_id"], "in_review",
             creative_hash=manifest["sha256"].get("tiktok_carousel.zip", ""),
             zip_sha256=_hl2.sha256(zip_path.read_bytes()).hexdigest())
    return {"plan": plan_dict, "proof": proof.to_dict(),
            "gates": gates, "manifest": manifest,
            "zip": str(zip_path), "receipt": receipt,
            "out_dir": str(out_dir)}


def run_variant(variant: dict, base_dir: Path | str = "store",
                receipts_path: Path | str = "receipts/content.jsonl") -> dict:
    """Build one per-business variant. Identity tokens only; consent-gated.

    variant comes from core.personalize.variant_spec. The personalization
    gate runs with the other five gates; research-only variants are stamped
    do-NOT-send on the receipt.
    """
    return run_carousel(
        variant["hook"], variant.get("template", "opportunity"),
        base_dir=base_dir, receipts_path=receipts_path,
        segment=variant.get("segment", "electrician"), variant=variant,
    )
