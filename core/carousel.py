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

from core.receipt import append_receipt
from render.slide import export_zip, render_slideshow
from slides.generate import generate_slides_deterministic, script_to_json


def _content_id(hook: str, template: str) -> str:
    h = hashlib.sha256(f"{hook}|{template}".encode()).hexdigest()[:12]
    return f"aoc_{h}"


def plan(hook: str, template: str = "opportunity", audience: str = "electrician",
         slide_count: int = 6, cta: str = "DM QUOTE for £499 setup") -> dict:
    """Stage 1: hook → slide script (JSON contract). No files, no LLM needed."""
    script = generate_slides_deterministic(hook, audience, template, slide_count)
    d = script_to_json(script)
    d["cta"] = cta
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
                 receipts_path: Path | str = "receipts/content.jsonl") -> dict:
    """Full local run: plan → render → export → receipt. No network. No publish."""
    base = Path(base_dir)
    plan_dict = plan(hook, template)
    out_dir = base / plan_dict["content_id"]
    manifest = render(plan_dict, out_dir)
    zip_path = export(manifest, out_dir)
    receipt = append_receipt(receipts_path, "carousel_built", {
        "content_id": plan_dict["content_id"],
        "hook": hook,
        "template": template,
        "slides": len(manifest["slides"]),
        "zip": str(zip_path),
    })
    return {"plan": plan_dict, "manifest": manifest, "zip": str(zip_path), "receipt": receipt}
