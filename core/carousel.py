"""Carousel orchestrator — hook → slides → PNGs → ZIP → receipt.

Stolen structure: ClipFactory 3-step versioned pipeline + ai-ugc JSON-as-contract.
Each stage independently re-runnable. Nothing publishes. Human posts manually
so trending audio can be chosen inside TikTok.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from core.gates import run_gates
from core.proof import proof_from_plan
from core.receipt import append_receipt
from core.validate import contact_sheet, validate_carousel
from render.slide import export_zip, render_slideshow
from slides.generate import generate_slides_deterministic, load_segment, script_to_json


def _content_id(hook: str, template: str) -> str:
    h = hashlib.sha256(f"{hook}|{template}".encode()).hexdigest()[:12]
    return f"aoc_{h}"


def plan(hook: str, template: str = "opportunity", audience: str = "electrician",
         slide_count: int = 6, cta: str | None = None, segment: str | None = None) -> dict:
    """Stage 1: hook → slide script (JSON contract). No files, no LLM needed.

    audience/segment select the skin (default electrician). CTA defaults to
    the segment close line unless explicitly passed.
    """
    seg = segment or audience
    from slides.generate import segment_close
    cta = cta or segment_close(seg)
    script = generate_slides_deterministic(hook, seg, template, slide_count)
    d = script_to_json(script)
    d["cta"] = cta
    d["segment"] = seg
    d["content_id"] = _content_id(hook, template)
    d["created_at"] = datetime.now(timezone.utc).isoformat()
    return d


def render(plan_dict: dict, out_dir: Path | str, font_path: str | None = None) -> dict:
    """Stage 2: script → 1080x1920 PNGs."""
    out_dir = Path(out_dir)
    # append CTA as final slide if not already the close
    slides = list(plan_dict["slides"])
    if plan_dict.get("cta") and not any(plan_dict["cta"] in s["text"] for s in slides[-1:]):
        slides.append({"text": plan_dict["cta"], "position": 0.5, "kind": "close", "tags": []})
    paths = render_slideshow(slides, out_dir, font_path=font_path)
    manifest = {
        "content_id": plan_dict["content_id"],
        "hook": plan_dict["hook"],
        "template": plan_dict["template"],
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


def run_carousel(hook: str, template: str = "opportunity", base_dir: Path | str = "store",
                 receipts_path: Path | str = "receipts/content.jsonl",
                 segment: str = "electrician", audience: str | None = None,
                 enforce_gates: bool = True, variant: dict | None = None) -> dict:
    """Full local run: plan → proof → gates → render → validate → export → receipt.

    Fail-closed like /content: gate failures write a FAIL receipt and raise;
    nothing renders. Pixel validation runs post-render; failures also FAIL.
    variant (optional): per-business spec from core.personalize — adds the
    personalization gate and stamps the receipt. No network. No publish.
    """
    base = Path(base_dir)
    seg = segment or (audience or "electrician")
    plan_dict = plan(hook, template, audience=seg, segment=seg)
    skin = load_segment(seg)

    # proof + gates BEFORE render
    proof = proof_from_plan(plan_dict, skin)
    gates = run_gates(plan_dict, proof, seg, receipts_path, variant=variant)
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

    out_dir = base / plan_dict["content_id"]
    manifest = render(plan_dict, out_dir)

    # pixel validation AFTER render, before export
    validation = validate_carousel(out_dir, manifest)
    sheet = contact_sheet(out_dir)
    manifest["validation"] = validation
    manifest["contact_sheet"] = sheet.name
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if enforce_gates and not validation["passed"]:
        bad = {k: v for k, v in validation["slides"].items() if not v["ok"]}
        append_receipt(receipts_path, "carousel_rejected", {
            "content_id": plan_dict["content_id"],
            "reason": "pixel validation",
            "failed_slides": bad,
        })
        raise ValueError(f"pixel validation failed: {list(bad)}")

    zip_path = export(manifest, out_dir)
    receipt_data = {
        "content_id": plan_dict["content_id"],
        "hook": hook,
        "template": template,
        "segment": seg,
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
    return {"plan": plan_dict, "proof": proof.to_dict(),
            "gates": gates, "manifest": manifest,
            "zip": str(zip_path), "receipt": receipt}


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
