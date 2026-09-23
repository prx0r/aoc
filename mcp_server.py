"""AOC MCP server — so powops / agents can query content status.

Tools: status, hooks, build_carousel, creative_rank, receipts_verify.
Read-only except build_carousel (writes local PNGs+ZIP, never publishes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent

TOOLS = [
    {"name": "aoc_status", "description": "What the factory can do: templates, hooks, receipts count", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "aoc_hooks", "description": "List hook bank for an audience", "inputSchema": {"type": "object", "properties": {"audience": {"type": "string", "default": "electrician"}}}},
    {"name": "aoc_build", "description": "Build a carousel locally (PNGs+ZIP, no publish)", "inputSchema": {"type": "object", "properties": {"hook": {"type": "string"}, "template": {"type": "string", "default": "opportunity"}}, "required": ["hook"]}},
    {"name": "aoc_rank", "description": "Rank creatives by leads/sales from memory", "inputSchema": {"type": "object", "properties": {"metric": {"type": "string", "default": "leads"}}}},
    {"name": "aoc_receipts", "description": "Verify receipt chain integrity", "inputSchema": {"type": "object", "properties": {}}},
]


def _handle(name: str, args: dict):
    sys.path.insert(0, str(ROOT))
    if name == "aoc_status":
        import yaml
        hooks = yaml.safe_load((ROOT / "assets/electrician/hooks.yaml").read_text())["hooks"]
        receipts = ROOT / "receipts/content.jsonl"
        n = sum(1 for _ in open(receipts)) if receipts.exists() else 0
        return {"templates": ["opportunity", "before_after", "faq", "social_proof", "demo"], "hooks": len(hooks), "receipts": n, "publish": "manual-only"}
    if name == "aoc_hooks":
        import yaml
        aud = args.get("audience", "electrician")
        hooks = yaml.safe_load((ROOT / "assets/electrician/hooks.yaml").read_text())["hooks"]
        return [h for h in hooks if h.get("audience", "owner_2_10_staff") in (aud, "owner_2_10_staff") or aud == "electrician"]
    if name == "aoc_build":
        from core.carousel import run_carousel
        return run_carousel(args["hook"], args.get("template", "opportunity"), base_dir=ROOT / "store", receipts_path=ROOT / "receipts/content.jsonl")
    if name == "aoc_rank":
        from core.memory import rank
        return [{"key": k, "runs": v.get("runs"), "totals": v.get("totals"), "cpqc": v.get("cpqc"), "cpsc": v.get("cpsc")} for k, v in rank(ROOT / "receipts/memory.json", args.get("metric", "leads"))]
    if name == "aoc_receipts":
        from core.receipt import verify_chain
        ok, msg = verify_chain(ROOT / "receipts/content.jsonl")
        return {"ok": ok, "message": msg}
    return {"error": f"unknown tool {name}"}


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            mid, method, params = req.get("id"), req.get("method", ""), req.get("params", {})
            if method == "initialize":
                res = {"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "aoc", "version": "0.1.0"}}}
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
