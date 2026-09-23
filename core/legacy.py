"""Legacy campaign import — map old IDs to current registry.

History: content IDs went aoc_<12hex> (hook+template only, collided) →
AOC-XXXXXXXX dirs (short display form, same collision) → AOC:<64hex>
(hook+CTA+caption+skin+renderer+offer). Old ZIPs are gitignored build
artifacts; this map preserves what each legacy record MEANS so history
stays queryable. Never delete historical records for missing ZIPs.
"""

from __future__ import annotations

import json
from pathlib import Path


def import_legacy(store_dir: Path | str = "store") -> dict:
    """Scan store dirs + campaigns.json + receipts. Returns migration map.

    Each entry: {legacy_id, dir, content_id|None, hook, status}
    status: current (resolvable to a full ID) | orphaned-artifact
    (files exist, ID predates registry) | missing (index references
    files .gitignore ate — record preserved anyway).
    """
    store = Path(store_dir)
    campaigns_fp = store / "campaigns.json"
    campaigns = {}
    if campaigns_fp.exists():
        try:
            campaigns = json.loads(campaigns_fp.read_text()).get("segments", {})
        except (json.JSONDecodeError, OSError):
            pass

    indexed: dict[str, dict] = {}
    for seg, items in campaigns.items():
        for it in items or []:
            cid = it.get("content_id", "")
            if cid:
                indexed[cid] = {"segment": seg, "hook": it.get("hook", ""),
                                "template": it.get("template", "")}

    mapping = []
    for d in sorted(store.iterdir()):
        if not d.is_dir():
            continue
        manifest_fp = d / "manifest.json"
        if manifest_fp.exists():
            try:
                m = json.loads(manifest_fp.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            cid = m.get("content_id", "")
            mapping.append({
                "dir": d.name,
                "content_id": cid,
                "legacy": cid.startswith("aoc_"),
                "hook": m.get("hook", ""),
                "zip_present": (d / "tiktok_carousel.zip").exists(),
                "status": "current" if cid.startswith("AOC:") else "orphaned-artifact",
            })
            indexed.pop(cid, None)
    # index entries with no surviving directory: history preserved anyway
    for cid, info in indexed.items():
        mapping.append({"dir": None, "content_id": cid,
                        "legacy": True, "hook": info.get("hook", ""),
                        "zip_present": False, "status": "missing"})
    return {"entries": mapping,
            "current": sum(1 for m in mapping if m["status"] == "current"),
            "orphaned": sum(1 for m in mapping if m["status"] == "orphaned-artifact"),
            "missing": sum(1 for m in mapping if m["status"] == "missing")}


if __name__ == "__main__":
    import sys
    out = import_legacy(sys.argv[1] if len(sys.argv) > 1 else "store")
    print(json.dumps({k: v for k, v in out.items() if k != "entries"}, indent=2))
    print(f"entries: {len(out['entries'])}")
