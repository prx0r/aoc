"""Creative memory — what produced leads, not just views.

Key: audience x hook x angle x slide_count x CTA x visual_style
Value: views, swipes, profile_visits, clicks, leads, sales

Prefer mutations of patterns that produced qualified leads.
"""

from __future__ import annotations

import json
from pathlib import Path


def _key(spec: dict) -> str:
    parts = [
        spec.get("audience", "?"),
        spec.get("hook_id", spec.get("hook", "?")[:40]),
        spec.get("angle", "?"),
        str(spec.get("slide_count", "?")),
        spec.get("cta", "?"),
        spec.get("visual_style", "dark"),
    ]
    return " | ".join(parts)


def record(memory_path: Path | str, spec: dict, metrics: dict) -> dict:
    p = Path(memory_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mem = {}
    if p.exists():
        mem = json.loads(p.read_text() or "{}")
    k = _key(spec)
    entry = mem.get(k, {"runs": 0, "totals": {}})
    entry["runs"] += 1
    entry["spec"] = spec
    totals = entry.setdefault("totals", {})
    for m, v in metrics.items():
        totals[m] = totals.get(m, 0) + (v or 0)
    # cost per qualified conversation + per customer — the only metrics that matter
    leads = totals.get("leads", 0)
    sales = totals.get("sales", 0)
    spend = totals.get("spend_gbp", 0)
    entry["cpqc"] = (spend / leads) if leads else None
    entry["cpsc"] = (spend / sales) if sales else None
    mem[k] = entry
    p.write_text(json.dumps(mem, indent=2))
    return entry


def rank(memory_path: Path | str, metric: str = "leads") -> list[tuple[str, dict]]:
    p = Path(memory_path)
    if not p.exists():
        return []
    mem = json.loads(p.read_text() or "{}")
    # rank by chosen metric, then by runs (prefer proven)
    return sorted(
        mem.items(),
        key=lambda kv: (kv[1].get("totals", {}).get(metric, 0), kv[1].get("runs", 0)),
        reverse=True,
    )
