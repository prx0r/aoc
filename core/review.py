"""Human review — the 15-point checklist as code + recorded sign-off.

Research consensus (AttentionClaw QA, Jumei skill files, viral-carousel-creator):
review is a checklist with pass/revise/reject + reason, not a vague approve
button. Automated checks run first; human judges taste at phone size;
the verdict is a receipt either way.
"""

from __future__ import annotations

import json
from pathlib import Path

# Each item: id, what, how checked (auto | human), source rule.
CHECKLIST = [
    ("hook-names-viewer", "Slide 1 names a specific viewer situation", "auto"),
    ("hook-matches-body", "Hook promise matches what follows", "human"),
    ("sequence-arc", "One structure only; order is load-bearing", "human"),
    ("each-slide-adds", "Every slide adds new info (no dupes)", "auto"),
    ("readable-phone-size", "Readable in <2s at phone size", "human"),
    ("contrast", "Extreme contrast, dark band present", "auto"),
    ("safe-zones", "Text clear of right edge + bottom 12%", "auto"),
    ("claims-sourced", "Every stat traces to proofs.yaml", "auto"),
    ("no-invented-numbers", "No figures without a source id", "auto"),
    ("visual-continuity", "Same font/palette/grid across slides", "human"),
    ("cta-single", "One CTA, matches viewer stage", "auto"),
    ("caption-supports", "Caption reinforces, not repeats, the hook", "human"),
    ("disclosure", "Fictional demos marked; no fake proof", "human"),
    ("trackable", "content_id + creative key assigned for measurement", "auto"),
    ("reviewer-recorded", "Human verdict with reason on file", "human"),
]


def run_review(out_dir: Path | str, plan: dict, gates: dict, validation: dict) -> dict:
    """Run the automated half of the checklist. Returns item verdicts."""
    out_dir = Path(out_dir)
    auto: dict[str, dict] = {}
    g = gates.get("gates", {})
    auto["hook-names-viewer"] = _v(g.get("hook-quality-v1", {}).get("ok", False), "gate hook-quality-v1")
    auto["each-slide-adds"] = _v(g.get("render-legible-v1", {}).get("ok", False), "gate render-legible-v1")
    vslides = (validation.get("slides", {}) or {})
    auto["contrast"] = _v(all(s.get("checks", {}).get("backdrop", {}).get("ok") for s in vslides.values()),
                          "pixel band luminance")
    auto["safe-zones"] = _v(all(s.get("checks", {}).get("margins", {}).get("ok") for s in vslides.values()),
                            "pixel margins")
    auto["claims-sourced"] = _v(g.get("evidence-fresh-v1", {}).get("ok", False), "gate evidence-fresh-v1")
    auto["no-invented-numbers"] = _v(g.get("claim-resolved-v1", {}).get("ok", False), "gate claim-resolved-v1")
    slides = plan.get("slides", [])
    closes = [s for s in slides if s.get("kind") == "close"]
    cta = plan.get("cta", "")
    # mirror render(): CTA appended unless last slide holds it or any DM close
    last = slides[-1].get("text", "") if slides else ""
    appended = 0 if (not cta or cta in last or "DM " in last) else 1
    final_closes = len(closes) + appended
    auto["cta-single"] = _v(final_closes == 1, f"{final_closes} close slide(s) post-render")
    auto["trackable"] = _v(bool(plan.get("content_id")), "content_id assigned")
    manual = [c for c in CHECKLIST if c[2] == "human"]
    return {
        "content_id": plan.get("content_id"),
        "automated": auto,
        "auto_passed": all(v["ok"] for v in auto.values()),
        "pending_human": [{"id": cid, "rule": rule} for cid, rule, _ in manual],
        "contact_sheet": str(out_dir / "contact_sheet.jpg"),
    }


def _v(ok: bool, detail: str) -> dict:
    return {"ok": bool(ok), "detail": detail}


def sign_off(receipts_path: Path | str, content_id: str, decision: str,
             reason: str, reviewer: str = "human",
             store_dir: Path | str | None = None) -> dict:
    """Record the human verdict — bound to the EXACT asset revision.

    Approval references the ZIP hash on disk right now; any re-render,
    CTA change, or edited claim mints a new content_id, so an approval
    can never authorise a different creative. revise/rejected need reasons;
    approvals need a human reviewer identity (never "system").
    """
    if decision not in ("approved", "revise", "rejected"):
        raise ValueError("decision must be approved|revise|rejected")
    if not reason:
        raise ValueError("a verdict without a reason is not a review")
    if decision == "approved":
        if not reviewer or reviewer == "system":
            raise ValueError("approval requires a human reviewer identity")
        asset = _asset_snapshot(content_id, store_dir)
        if asset is None:
            raise ValueError(f"cannot approve missing/changed creative {content_id[:24]}…")
    else:
        asset = _asset_snapshot(content_id, store_dir)
    from core.receipt import append_receipt
    return append_receipt(receipts_path, "reviewed", {
        "content_id": content_id, "decision": decision,
        "reason": reason, "reviewer": reviewer,
        "asset": asset or {},
    })


def _asset_snapshot(content_id: str, store_dir: Path | str | None) -> dict | None:
    """Hash snapshot of the built asset, or None if missing/changed."""
    import hashlib as _hl
    import json as _json
    from pathlib import Path as _P
    root = _P(store_dir) if store_dir else _P(__file__).parent.parent / "store"
    for manifest_fp in sorted(root.glob("*/manifest.json")):
        try:
            m = _json.loads(manifest_fp.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if m.get("content_id") != content_id:
            continue
        out = manifest_fp.parent
        files = {}
        for name, expect in (m.get("sha256") or {}).items():
            fp = out / name
            if not fp.exists():
                return None
            got = _hl.sha256(fp.read_bytes()).hexdigest()
            if got != expect:
                return None  # changed since build — approval refused
            files[name] = got
        zp = out / "tiktok_carousel.zip"
        return {"zip_sha256": _hl.sha256(zp.read_bytes()).hexdigest() if zp.exists() else "",
                "slides": files,
                "contact_sheet": (out / "contact_sheet.jpg").name
                if (out / "contact_sheet.jpg").exists() else ""}
    return None
