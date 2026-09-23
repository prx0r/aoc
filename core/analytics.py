"""Analytics — append-only snapshots → derived rates → learnings.

Honest stack (per TikLiveAPI analysis + KeyAPI dashboard guide):
- Watch time / completion are NOT in any public API. Proxies only.
- collect_count (saves) / views = best public proxy for completion.
- Engagement velocity normalized per bucket; per-bucket regression needs
  your own Creator Studio CSV export joined on post id.
- Store raw snapshots with timestamps (append, never overwrite); derive after.

/content's measure() only records whatever dict you pass. This module adds:
snapshot schema, derived metrics, CSV import, and a learnings compiler
that feeds core/memory.py (best hooks/times/styles).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def record_snapshot(snapshots_path: Path | str, post_url: str, content_id: str = "",
                    metrics: dict | None = None, source: str = "manual") -> dict:
    """Append one raw snapshot. Never overwrites. Returns the stored row."""
    p = Path(snapshots_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "at": datetime.now(timezone.utc).isoformat(),
        "post_url": post_url,
        "content_id": content_id,
        "source": source,  # manual | studio_csv | display_api | business_api | scraper
        "metrics": metrics or {},
    }
    with open(p, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


DERIVE_VERSION = 1
DERIVE_FORMULA_ID = "aoc.derive"


def derive(metrics: dict) -> dict:
    """Derived rates from raw counts. All safe-divided.

    Versioned (formula aoc.derive v1): a tweak must bump DERIVE_VERSION so
    history isn't silently rewritten (ported from ographuk signal registry).
    """
    return derive_v1(metrics)


def derive_v1(metrics: dict) -> dict:
    views = max(metrics.get("views", 0), 1)
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", metrics.get("collect_count", 0))
    profile_visits = metrics.get("profile_visits", 0)
    clicks = metrics.get("clicks", 0)
    leads = metrics.get("leads", 0)
    sales = metrics.get("sales", 0)
    spend = metrics.get("spend_gbp", 0)
    return {
        "engagement_rate": round((likes + comments + shares) / views * 100, 2),
        "save_rate": round(saves / views * 100, 2),  # completion proxy
        "share_rate": round(shares / views * 100, 2),
        "comment_rate": round(comments / views * 100, 2),
        "profile_rate": round(profile_visits / views * 100, 2),
        "cpqc": round(spend / leads, 2) if leads else None,  # cost per qualified convo
        "cpsc": round(spend / sales, 2) if sales else None,  # cost per customer
    }


def import_studio_csv(csv_path: Path | str, snapshots_path: Path | str,
                      url_column: str = "post_url") -> int:
    """Import a TikTok Studio export. Returns rows appended."""
    n = 0
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            url = row.get(url_column, "")
            if not url:
                continue
            metrics = {}
            for k in ("views", "likes", "comments", "shares", "saves",
                      "profile_visits", "clicks"):
                try:
                    metrics[k] = int(float(row.get(k, 0) or 0))
                except (ValueError, TypeError):
                    pass
            record_snapshot(snapshots_path, url,
                            content_id=row.get("content_id", ""),
                            metrics=metrics, source="studio_csv")
            n += 1
    return n


def compile_learnings(snapshots_path: Path | str, memory_path: Path | str) -> dict:
    """Snapshots → memory.json ranking inputs. Best hooks by leads, then saves.

    Joins each snapshot to its content spec (hook/angle/template via receipts)
    where content_id matches; unattributed snapshots still count toward totals.
    """
    snaps = []
    p = Path(snapshots_path)
    if p.exists():
        with open(p) as f:
            snaps = [json.loads(ln) for ln in f if ln.strip()]
    from core.memory import record as mem_record
    ranked = []
    for s in snaps:
        m = s.get("metrics", {})
        d = derive(m)
        spec = {"audience": "tiktok", "hook": s.get("content_id", s.get("post_url", ""))[:40],
                "angle": "posted", "slide_count": 0, "cta": "", "visual_style": ""}
        mem_record(memory_path, spec, {**m,
                                       "engagement_rate": d["engagement_rate"],
                                       "save_rate": d["save_rate"]})
        ranked.append({"url": s.get("post_url"), "derived": d})
    ranked.sort(key=lambda r: (r["derived"]["cpqc"] is None,
                               r["derived"]["cpqc"] if r["derived"]["cpqc"] is not None else 0))
    return {"snapshots": len(snaps), "ranked": ranked}
