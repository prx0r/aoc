"""E2E: every segment → plan → PNGs → ZIP → receipts → MCP. No network."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.carousel import export, plan, render, run_carousel  # noqa: E402
from core.memory import rank, record  # noqa: E402
from core.receipt import append_receipt, verify_chain  # noqa: E402

SEGMENTS = {
    "electrician": "UK electricians — still doing quotes at 9pm?",
    "beautician": "Salon owners — how much did no-shows cost you last month?",
    "plumber": "Plumbers — who triages while you're under a boiler?",
    "sole_trader": "Sole trader — can customers find you on Google?",
}


def test_e2e_all_segments_build_valid_carousels(tmp_path):
    from PIL import Image
    for seg, hook in SEGMENTS.items():
        p = plan(hook, "opportunity", segment=seg)
        assert p["segment"] == seg, seg
        assert len(p["slides"]) >= 5, seg
        out = tmp_path / seg
        m = render(p, out)
        assert len(m["slides"]) >= 5, seg
        for name in m["slides"]:
            fp = out / name
            assert fp.exists(), (seg, name)
            with open(fp, "rb") as f:
                assert f.read(2) == b"\xff\xd8", (seg, name)  # JPEG magic
            with Image.open(fp) as im:
                assert im.size == (1080, 1920), (seg, name, im.size)
        z = export(m, out)
        assert z.exists() and z.stat().st_size > 10_000, seg
        # CTA present on close
        assert p["cta"] in p["slides"][-1]["text"] or "DM " in p["slides"][-1]["text"], seg


def test_e2e_run_carousel_writes_receipt(tmp_path):
    rp = tmp_path / "content.jsonl"
    r = run_carousel(
        "Which of these would you automate first?",
        "opportunity",
        base_dir=tmp_path / "store",
        receipts_path=rp,
        segment="plumber",
    )
    assert Path(r["zip"]).exists()
    assert r["plan"]["segment"] == "plumber"
    assert r["receipt"]["data"]["segment"] == "plumber"
    ok, _ = verify_chain(rp)
    assert ok


def test_e2e_memory_ranks_leads_over_views(tmp_path):
    mem = tmp_path / "memory.json"
    record(mem, {"audience": "e", "hook": "viral", "angle": "q", "slide_count": 6, "cta": "DM", "visual_style": "dark"},
           {"views": 50000, "leads": 0, "spend_gbp": 0})
    record(mem, {"audience": "e", "hook": "buyer", "angle": "q", "slide_count": 6, "cta": "DM", "visual_style": "dark"},
           {"views": 400, "leads": 4, "sales": 1, "spend_gbp": 70})
    top = rank(mem, "leads")[0]
    assert top[1]["totals"]["leads"] == 4
    assert top[1]["cpqc"] == 70 / 4


def test_e2e_mcp_tools_queryable():
    root = Path(__file__).parent.parent
    def call(payload: dict) -> dict:
        proc = subprocess.run(
            [sys.executable, str(root / "mcp_server.py")],
            input=json.dumps(payload), capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout.strip())

    tools = call({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    names = [t["name"] for t in tools["result"]["tools"]]
    assert {"aoc_status", "aoc_hooks", "aoc_build", "aoc_rank", "aoc_receipts"} <= set(names)

    status = call({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": "aoc_status", "arguments": {}}})
    body = json.loads(status["result"]["content"][0]["text"])
    assert body["publish"] == "manual-only"
    assert body["hooks"] >= 30  # 16+8+8+7 across skins

    hooks = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "aoc_hooks", "arguments": {"segment": "beautician"}}})
    bhooks = json.loads(hooks["result"]["content"][0]["text"])
    assert any("no-show" in h["text"].lower() for h in bhooks), "beautician skin leaked"


def test_e2e_state_machine_full_lifecycle():
    from core.state import ContentStatus, create_content, transition
    c = create_content("e2e", "hook", [], "opportunity")
    for target in [ContentStatus.DRAFT, ContentStatus.IN_REVIEW, ContentStatus.APPROVED,
                   ContentStatus.SCHEDULED, ContentStatus.PUBLISHED, ContentStatus.MEASURED]:
        c = transition(c, target)
    assert c["status"] == "measured"
    assert any(h["to"] == "in_review" for h in c["history"])
