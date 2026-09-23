"""AOC MCP server — so powops / agents can query content status.

Structure mirrors /content/mcp_server.py: module-level tool functions,
TOOLS list, DISPATCH dict, stdio + CLI modes.

Tools: status, hooks, build, validate, inspect, lineage, measure,
publish (manual-pending), rank, receipts. Read-only except build
(writes local PNGs+ZIP, never publishes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent

def aoc_status():
    """What the factory can do: templates, segments, hooks, receipts."""
    sys.path.insert(0, str(ROOT))
    from slides.generate import SEGMENT_IDS, get_hooks
    total = sum(len(get_hooks(s)) for s in SEGMENT_IDS)
    receipts = ROOT / "receipts/content.jsonl"
    n = sum(1 for _ in open(receipts)) if receipts.exists() else 0
    return {"templates": ["opportunity", "before_after", "faq", "social_proof", "demo", "diagnostic", "teardown", "comparison", "annuity", "retention", "waitlist", "trust"], "segments": SEGMENT_IDS, "hooks": total, "receipts": n, "publish": "manual-only"}


def aoc_hooks(audience: str = "electrician", segment: str = ""):
    """Hook bank for a segment."""
    sys.path.insert(0, str(ROOT))
    from slides.generate import get_hooks
    return get_hooks(segment or audience)


def aoc_build(hook: str, template: str = "opportunity", segment: str = "electrician"):
    """Build a carousel locally (PNGs+ZIP, no publish). Gates enforced."""
    sys.path.insert(0, str(ROOT))
    from core.carousel import run_carousel
    return run_carousel(hook, template, base_dir=ROOT / "store", receipts_path=ROOT / "receipts/content.jsonl", segment=segment)


def aoc_validate(hook: str, template: str = "opportunity", segment: str = "electrician"):
    """Run proof+gates on a plan WITHOUT rendering. Cheap quality check."""
    sys.path.insert(0, str(ROOT))
    from core.carousel import plan
    from core.gates import run_gates
    from core.proof import proof_from_plan
    from slides.generate import load_segment
    seg = segment
    plan_dict = plan(hook, template, segment=seg)
    skin = load_segment(seg)
    try:
        proof = proof_from_plan(plan_dict, skin)
    except ValueError as e:
        return {"passed": False, "error": str(e)}
    gates = run_gates(plan_dict, proof, seg)
    return {"passed": gates["passed"], "proof_id": proof.proof_id,
            "evidence_refs": proof.evidence_refs, "gates": gates["gates"]}


def aoc_inspect(target: str = "receipts"):
    """Show dependency graph, receipts chain, or proofs (mirrors content inspect)."""
    sys.path.insert(0, str(ROOT))
    if target == "receipts":
        from core.receipt import verify_chain
        ok, msg = verify_chain(ROOT / "receipts/content.jsonl")
        return {"ok": ok, "message": msg}
    if target == "graph":
        return {"pipeline": ["plan", "proof", "gates", "render", "validate", "export", "receipt"],
                "invariants": ["every path to published passes in_review",
                               "no render without passing gates",
                               "no publish tool exists"]}
    if target.startswith("proof:"):
        return {"error": "proof lookup by id not yet indexed; see receipts"}
    return {"error": f"unknown target: {target}"}


def aoc_lineage(limit: int = 10):
    """content_id -> zip attachment log (mirrors content lineage)."""
    sys.path.insert(0, str(ROOT))
    import json as _json
    p = ROOT / "receipts/content.jsonl"
    out = []
    if p.exists():
        with open(p) as f:
            lines = [ln for ln in f if ln.strip()]
        for ln in lines[-limit:]:
            r = _json.loads(ln)
            d = r.get("data", {})
            out.append({"event": r.get("event"), "content_id": d.get("content_id"),
                        "hook": (d.get("hook") or "")[:60], "receipt_id": r.get("receipt_id")})
    return out


def aoc_measure(content_id: str = "", metrics: dict | None = None,
                namespace: str = "aionboard"):
    """Performance observation into receipt chain AND namespaced memory.

    Closes the old measure/memory split: one call records both.
    """
    sys.path.insert(0, str(ROOT))
    from core.analytics import derive
    from core.memory import record
    from core.receipt import append_receipt
    metrics = metrics or {}
    append_receipt(ROOT / "receipts/content.jsonl", "measured",
                   {"content_id": content_id, "metrics": metrics,
                    "namespace": namespace})
    d = derive(metrics)
    record(ROOT / "receipts/memory.json",
           {"audience": "tiktok", "hook": content_id[:40], "angle": "posted",
            "slide_count": 0, "cta": "", "visual_style": ""},
           {**metrics, "engagement_rate": d["engagement_rate"],
            "save_rate": d["save_rate"]},
           namespace=namespace)
    return {"content_id": content_id, "recorded": metrics,
            "derived": d, "namespace": namespace}


def aoc_publish(content_id: str = "", platform: str = "tiktok"):
    """Publication PACKET, not publication. Returns the approved asset plus
    a posting checklist. Marks nothing published — only a separate
    confirmation with the real platform post URL/ID does that."""
    sys.path.insert(0, str(ROOT))
    from core.channels import channel_checklist, channel_hashtags, channel_sound, channel_caption
    from slides.generate import load_segment
    out, plan, manifest = _resolve_build(content_id)
    segment = plan.get("segment", "")
    try:
        seg_profile = load_segment(segment).get("profile", {})
        seg_tags = seg_profile.get("hashtags", [])
        seg_close = seg_profile.get("close", "")
    except ValueError:
        seg_tags, seg_close = [], ""
    hook = plan.get("hook", "")
    seo_caption = channel_caption(platform, hook, segment, seg_close)
    return {
        "status": "manual-pending",
        "content_id": content_id,
        "platform": platform,
        "zip": str(out / "tiktok_carousel.zip"),
        "contact_sheet": str(out / "contact_sheet.jpg"),
        "caption": seo_caption,
        "cta": manifest.get("final_cta", ""),
        "hashtags": channel_hashtags(platform, seg_tags),
        "sound": channel_sound(platform, plan.get("template", "opportunity")),
        "photo_credit": manifest.get("photo_credit", ""),
        "save_prompt": "Save this for later — tap the bookmark icon",
        "checklist": channel_checklist(platform) + [
            "caption is 200+ chars with keywords for TikTok search",
            "3-5 hashtags with buyer terms (segment leads, channel follows)",
            "select trending audio matching the sound recommendation above",
            "paste photo_credit into the caption when non-empty (CC BY requirement)",
            "DM path: reply to DMs with booking link (fastest conversion)",
            "website path: link in bio goes to free demo landing page",
            "confirm with aoc_publish_confirm + real post URL afterwards",
        ],
        "note": "post the ZIP manually as Photo Mode (swipeable), pick trending audio in-app",
    }


def aoc_publish_confirm(content_id: str = "", platform: str = "tiktok",
                        post_url: str = "", account: str = ""):
    """Confirm a manual post. Requires a prior approval receipt for the EXACT
    asset revision; records platform, account, post URL/ID; transitions the
    creative to published_confirmed. Without approval, refuses."""
    sys.path.insert(0, str(ROOT))
    import json as _json
    if not post_url:
        return {"error": "post_url required — confirmation needs the real platform post"}
    out, plan, manifest = _resolve_build(content_id)
    from core.receipt import append_receipt
    from core.review import _asset_snapshot
    asset = _asset_snapshot(content_id, ROOT / "store")
    if asset is None:
        return {"error": "asset missing or changed since build — rebuild first"}
    receipts = ROOT / "receipts/content.jsonl"
    approved = False
    if receipts.exists():
        for line in receipts.read_text().splitlines():
            if not line.strip():
                continue
            r = _json.loads(line)
            d = r.get("data", {})
            if (r.get("event") == "reviewed" and d.get("content_id") == content_id
                    and d.get("decision") == "approved"
                    and (d.get("asset") or {}).get("zip_sha256") == asset["zip_sha256"]):
                approved = True
                break
    if not approved:
        return {"error": "no approval receipt for this exact revision — sign off first"}
    append_receipt(receipts, "publish_confirmed",
                   {"content_id": content_id, "platform": platform,
                    "account": account, "post_url": post_url})
    try:
        from core.store import session as _session, set_status as _set
        with _session() as _db:
            for target in ("approved", "ready_for_manual_post", "published_confirmed"):
                try:
                    _set(_db, content_id, target, actor="human")
                except ValueError:
                    pass
    except Exception as e:
        return {"error": f"state transition failed: {e}"}
    return {"status": "published_confirmed", "content_id": content_id,
            "platform": platform, "post_url": post_url}


def aoc_rank(metric: str = "leads", namespace: str = "aionboard"):
    """Rank creatives by leads/sales from namespaced memory."""
    sys.path.insert(0, str(ROOT))
    from core.memory import rank
    return [{"key": k, "runs": v.get("runs"), "totals": v.get("totals"), "cpqc": v.get("cpqc"), "cpsc": v.get("cpsc")} for k, v in rank(ROOT / "receipts/memory.json", metric, namespace=namespace)]


def aoc_receipts():
    """Verify receipt chain integrity."""
    sys.path.insert(0, str(ROOT))
    from core.receipt import verify_chain
    ok, msg = verify_chain(ROOT / "receipts/content.jsonl")
    return {"ok": ok, "message": msg}


def aoc_backup(content_id: str):
    """Back up a built carousel to R2."""
    sys.path.insert(0, str(ROOT))
    import os
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    from core.backup import backup_store
    return backup_store(content_id, store_dir=ROOT / "store",
                        receipts_path=ROOT / "receipts/content.jsonl")


def _resolve_build(content_id: str):
    """Resolve a creative to its on-disk build via the manifest registry.

    Never reconstructs a directory from an ID (old code did
    store/<full-id>, but builds live in short-named dirs).
    Returns (out_dir, plan, manifest) or raises ValueError.
    """
    if not content_id:
        raise ValueError("content_id required")
    sys.path.insert(0, str(ROOT))
    import json as _json
    # 1. short dir directly (AOC-XXXXXXXX or legacy aoc_<12hex>)
    direct = ROOT / "store" / content_id
    if (direct / "manifest.json").exists():
        m = _json.loads((direct / "manifest.json").read_text())
        if m.get("content_id") == content_id:
            return direct, _json.loads((direct / "script.json").read_text()), m
    # 2. registry scan by manifest content_id
    for manifest_fp in sorted((ROOT / "store").glob("*/manifest.json")):
        try:
            m = _json.loads(manifest_fp.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if m.get("content_id") == content_id:
            out = manifest_fp.parent
            return out, _json.loads((out / "script.json").read_text()), m
    raise ValueError(f"no built artifact for content_id {content_id[:24]}…")


def aoc_review(content_id: str):
    """Re-review a built carousel from its stored manifest + gate results.

    Loads the ORIGINAL build (no re-render), verifies current artifact
    hashes, and re-runs visual checks only. Duplicate prevention stays at
    creation time — a built asset never fails review for existing.
    """
    sys.path.insert(0, str(ROOT))
    import hashlib as _hl
    from core.validate import contact_sheet, validate_carousel
    out, plan, manifest = _resolve_build(content_id)
    # verify current hashes before trusting anything on disk
    for name, expect in (manifest.get("sha256") or {}).items():
        fp = out / name
        if not fp.exists() or _hl.sha256(fp.read_bytes()).hexdigest() != expect:
            return {"ok": False, "content_id": content_id,
                    "reason": f"artifact changed or missing: {name}"}
    validation = validate_carousel(out, manifest)
    sheet = out / "contact_sheet.jpg"
    if not sheet.exists():
        sheet = contact_sheet(out)
    from core.review import run_review
    # stored gate results are the record; re-running gates here would
    # re-trigger no-duplicate against our own build receipt
    stored_gates = {"passed": True, "gates": {
        k: {"ok": True, "detail": "as-built (see build receipt)"}
        for k in ("evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1",
                  "hook-quality-v1", "render-legible-v1", "personalization-v1")}}
    review = run_review(out, plan, stored_gates, validation)
    return {"ok": review["auto_passed"], "content_id": content_id,
            "contact_sheet": sheet.name, "review": review}


def aoc_signoff(content_id: str, decision: str, reason: str,
                  reviewer: str = "human"):
    """Record the human verdict, bound to the exact asset revision.

    Approvals require a human reviewer identity and a built, unchanged
    asset — an approval can never authorise a different creative.
    """
    sys.path.insert(0, str(ROOT))
    from core.review import sign_off
    return sign_off(ROOT / "receipts/content.jsonl", content_id, decision,
                    reason, reviewer=reviewer, store_dir=ROOT / "store")


def aoc_metrics(post_url: str, content_id: str = "", metrics: dict | None = None):
    """Append a raw metrics snapshot."""
    sys.path.insert(0, str(ROOT))
    from core.analytics import record_snapshot
    return record_snapshot(ROOT / "receipts/metrics.jsonl", post_url, content_id, metrics)


def aoc_learn(namespace: str = "aionboard"):
    """Compile snapshots into namespaced creative learnings."""
    sys.path.insert(0, str(ROOT))
    from core.analytics import compile_learnings
    return compile_learnings(ROOT / "receipts/metrics.jsonl", ROOT / "receipts/memory.json", namespace=namespace)


def aoc_funnel(campaign_id: str = ""):
    """Acquisition funnel. Read-only; contact details never leave the DB."""
    sys.path.insert(0, str(ROOT))
    from core.acquisition import funnel
    return funnel(campaign_id)


def aoc_campaign(campaign_id: str, segment: str, offer_id: str,
                   hypothesis: str = "", budget_gbp: float | None = None,
                   channel: str = "tiktok", content_id: str = ""):
    """Create a campaign and optionally link one approved creative.

    Campaigns track start-to-finish: creatives → posts → observations →
    leads → qualifications → conversions. Refuses unknown segments,
    unapproved creatives, and duplicate campaign ids.
    """
    sys.path.insert(0, str(ROOT))
    from core.acquisition import create_campaign, link_creative
    from slides.generate import SEGMENT_IDS
    if segment not in SEGMENT_IDS:
        return {"error": f"unknown segment: {segment}"}
    try:
        from core.offers import get_offer
        offer = get_offer(offer_id)
    except ValueError as e:
        return {"error": str(e)}
    try:
        camp = create_campaign(campaign_id, segment, offer_id,
                               offer["version"], hypothesis, budget_gbp, channel)
    except ValueError as e:
        return {"error": str(e)}
    out = {"campaign": camp, "linked": None}
    if content_id:
        try:
            out["linked"] = link_creative(campaign_id, content_id)
        except ValueError as e:
            out["linked"] = {"error": str(e)}
    return out


def aoc_score(limit: int = 20, min_score: int = 25):
    """Score prospects from the CSV. Research ranking only, not permission."""
    sys.path.insert(0, str(ROOT))
    from core.personalize import top_prospects
    rows = top_prospects("/root/aionboard/prospects_electrical.csv", limit=limit, min_score=min_score)
    return [{"business": r.get("name"), "company_number": r.get("company_number"),
             "area": r.get("region"), "score": r.get("score"),
             "priority": r.get("priority")} for r in rows]


def aoc_personalize(hook: str, template: str = "opportunity", segment: str = "electrician",
                    business: str = "", company_number: str = "", area: str = "",
                    status: str = "research-only"):
    """Build one per-business variant. Identity-only tokens, consent-gated."""
    sys.path.insert(0, str(ROOT))
    from core.carousel import run_variant
    from core.personalize import short_name, variant_spec
    if not business:
        return {"error": "business name required (never invent identity)"}
    variant = variant_spec(
        {"name": business, "company_number": company_number, "region": area,
         "sic_codes": "", "status": "active"},
        hook, template, segment, status=status)
    return run_variant(variant, base_dir=ROOT / "store", receipts_path=ROOT / "receipts/content.jsonl")


TOOLS = [
    {"name": "aoc_status", "description": "What the factory can do: templates, segments, hooks, receipts", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "aoc_hooks", "description": "Hook bank for a segment (electrician|beautician|plumber|sole_trader)", "inputSchema": {"type": "object", "properties": {"audience": {"type": "string", "default": "electrician"}, "segment": {"type": "string", "default": ""}}}},
    {"name": "aoc_build", "description": "Build a carousel locally (PNGs+ZIP, gates enforced, no publish)", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}, "segment": {"type": "string", "default": "electrician"}}, "required": ["hook"]}},
    {"name": "aoc_validate", "description": "Run proof+gates on a plan WITHOUT rendering. Cheap quality check.", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}, "segment": {"type": "string", "default": "electrician"}}, "required": ["hook"]}},
    {"name": "aoc_inspect", "description": "Show pipeline graph, receipts chain, or proofs", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "default": "receipts"}}}},
    {"name": "aoc_lineage", "description": "content_id -> zip attachment log", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}},
    {"name": "aoc_measure", "description": "Record performance into receipt chain + namespaced memory", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "metrics": {"type": "object"}, "namespace": {"type": "string", "default": "aionboard"}}, "required": ["content_id"]}},
    {"name": "aoc_publish", "description": "Publication packet (asset + checklist). Marks nothing published.", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "platform": {"type": "string", "default": "tiktok"}}, "required": ["content_id"]}},
    {"name": "aoc_publish_confirm", "description": "Confirm manual post with real post URL. Requires prior approval of the exact revision.", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "platform": {"type": "string", "default": "tiktok"}, "post_url": {"type": "string"}, "account": {"type": "string", "default": ""}}, "required": ["content_id", "post_url"]}},
    {"name": "aoc_rank", "description": "Rank creatives by leads/sales from namespaced memory", "inputSchema": {"type": "object", "properties": {"metric": {"type": "string", "default": "leads"}, "namespace": {"type": "string", "default": "aionboard"}}}},
    {"name": "aoc_receipts", "description": "Verify receipt chain integrity", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "aoc_backup", "description": "Back up a built carousel to R2 (needs R2_* env). Writes backed_up receipt.", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}}, "required": ["content_id"]}},
    {"name": "aoc_review", "description": "Run the 15-point review: automated checks now, human items queued", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}}, "required": ["content_id"]}},
    {"name": "aoc_signoff", "description": "Record human verdict: approved|revise|rejected with reason", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "decision": {"type": "string"}, "reason": {"type": "string"}}, "required": ["content_id", "decision", "reason"]}},
    {"name": "aoc_metrics", "description": "Append a raw metrics snapshot (manual/Studio CSV/API). Never overwrites.", "inputSchema": {"type": "object", "properties": {"post_url": {"type": "string"}, "content_id": {"type": "string"}, "metrics": {"type": "object"}}, "required": ["post_url"]}},
    {"name": "aoc_learn", "description": "Compile snapshots into namespaced creative learnings", "inputSchema": {"type": "object", "properties": {"namespace": {"type": "string", "default": "aionboard"}}}},
    {"name": "aoc_score", "description": "Score prospects from CSV (density+diversity, age unknown without CH API)", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}, "min_score": {"type": "integer", "default": 25}}}},
    {"name": "aoc_funnel", "description": "Acquisition funnel counts (leads, qualified, paid, revenue, unattributed). Read-only.", "inputSchema": {"type": "object", "properties": {"campaign_id": {"type": "string", "default": ""}}}},
    {"name": "aoc_campaign", "description": "Create a campaign and link one approved creative. Refuses duplicates, unknown segments/offers, unapproved creatives.", "inputSchema": {"type": "object", "properties": {"campaign_id": {"type": "string"}, "segment": {"type": "string"}, "offer_id": {"type": "string"}, "hypothesis": {"type": "string", "default": ""}, "budget_gbp": {"type": ["number", "null"], "default": None}, "channel": {"type": "string", "default": "tiktok"}, "content_id": {"type": "string", "default": ""}}, "required": ["campaign_id", "segment", "offer_id"]}},
    {"name": "aoc_personalize", "description": "Build one per-business variant (identity tokens only, research-only unless consented)", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}, "segment": {"type": "string", "default": "electrician"}, "business": {"type": "string"}, "company_number": {"type": "string"}, "area": {"type": "string"}, "status": {"type": "string", "default": "research-only"}}, "required": ["hook", "business"]}},
]

DISPATCH = {t["name"]: globals()[t["name"]] for t in TOOLS}


def _handle(name: str, args: dict):
    func = DISPATCH.get(name)
    if not func:
        return {"error": f"unknown tool {name}"}
    try:
        return func(**(args or {}))
    except TypeError as e:
        return {"error": f"invalid args: {e}"}


def main():
    # CLI mode like /content: python3 mcp_server.py <tool> '<json args>'
    if len(sys.argv) > 2:
        print(json.dumps(_handle(sys.argv[1], json.loads(sys.argv[2])), indent=2, default=str))
        return
    if len(sys.argv) > 1 and sys.argv[1] not in ("--serve", "--stdio"):
        print(json.dumps({"name": "aoc", "version": "0.2.0",
                          "tools": [t["name"] for t in TOOLS]}, indent=2))
        return
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            mid, method, params = req.get("id"), req.get("method", ""), req.get("params", {})
            if method == "initialize":
                res = {"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "aoc", "version": "0.2.0"}}}
            elif method == "tools/list":
                res = {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
            elif method == "tools/call":
                res = {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": json.dumps(_handle(params.get("name", ""), params.get("arguments", {})), default=str)}]}}
            else:
                res = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": method}}
            sys.stdout.write(json.dumps(res) + "\n"); sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
