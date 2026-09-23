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
    return {"templates": ["opportunity", "before_after", "faq", "social_proof", "demo", "diagnostic", "teardown", "comparison"], "segments": SEGMENT_IDS, "hooks": total, "receipts": n, "publish": "manual-only"}


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


def aoc_measure(content_id: str = "", metrics: dict | None = None):
    """Performance observation back into the receipt chain (mirrors content measure)."""
    sys.path.insert(0, str(ROOT))
    from core.memory import record
    from core.receipt import append_receipt
    metrics = metrics or {}
    append_receipt(ROOT / "receipts/content.jsonl", "measured",
                   {"content_id": content_id, "metrics": metrics})
    return {"content_id": content_id, "recorded": metrics}


def aoc_publish(content_id: str = "", platform: str = "tiktok"):
    """Platform adapter. Manual until an uploader is wired; receipt says manual-pending."""
    sys.path.insert(0, str(ROOT))
    from core.receipt import append_receipt
    append_receipt(ROOT / "receipts/content.jsonl", "publish",
                   {"content_id": content_id, "platform": platform, "status": "manual-pending",
                    "note": "post the ZIP manually to pick trending audio in-app"})
    return {"status": "manual-pending", "content_id": content_id, "platform": platform}


def aoc_rank(metric: str = "leads"):
    """Rank creatives by leads/sales from memory."""
    sys.path.insert(0, str(ROOT))
    from core.memory import rank
    return [{"key": k, "runs": v.get("runs"), "totals": v.get("totals"), "cpqc": v.get("cpqc"), "cpsc": v.get("cpsc")} for k, v in rank(ROOT / "receipts/memory.json", metric)]


def aoc_receipts():
    """Verify receipt chain integrity."""
    sys.path.insert(0, str(ROOT))
    from core.receipt import verify_chain
    ok, msg = verify_chain(ROOT / "receipts/content.jsonl")
    return {"ok": ok, "message": msg}


TOOLS = [
    {"name": "aoc_status", "description": "What the factory can do: templates, segments, hooks, receipts", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "aoc_hooks", "description": "Hook bank for a segment (electrician|beautician|plumber|sole_trader)", "inputSchema": {"type": "object", "properties": {"audience": {"type": "string", "default": "electrician"}, "segment": {"type": "string", "default": ""}}}},
    {"name": "aoc_build", "description": "Build a carousel locally (PNGs+ZIP, gates enforced, no publish)", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}, "segment": {"type": "string", "default": "electrician"}}, "required": ["hook"]}},
    {"name": "aoc_validate", "description": "Run proof+gates on a plan WITHOUT rendering. Cheap quality check.", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}, "segment": {"type": "string", "default": "electrician"}}, "required": ["hook"]}},
    {"name": "aoc_inspect", "description": "Show pipeline graph, receipts chain, or proofs", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "default": "receipts"}}}},
    {"name": "aoc_lineage", "description": "content_id -> zip attachment log", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}},
    {"name": "aoc_measure", "description": "Record performance metrics into receipt chain + memory", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "metrics": {"type": "object"}}, "required": ["content_id"]}},
    {"name": "aoc_publish", "description": "Manual-pending publish adapter (no auto-post by design)", "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}, "platform": {"type": "string", "default": "tiktok"}}, "required": ["content_id"]}},
    {"name": "aoc_rank", "description": "Rank creatives by leads/sales from memory", "inputSchema": {"type": "object", "properties": {"metric": {"type": "string", "default": "leads"}}}},
    {"name": "aoc_receipts", "description": "Verify receipt chain integrity", "inputSchema": {"type": "object", "properties": {}}},
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
