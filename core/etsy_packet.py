"""Etsy listing packets — 10-slot photo plan + copy validation per product.

A packet is the complete upload set for one listing: which image goes in
which slot, what needs real photography vs typography cards, validated copy,
and the silent video. Manual upload (Shop Manager) — matches house doctrine.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# Slot plan: (slot, kind, needs) — kind photo requires real photography,
# type allows a typography card from render/etsy.py.
SLOTS = [
    (1, "hero", "type", "product name + concept price, centered, safe zone"),
    (2, "lifestyle", "photo", "product in use / garden context"),
    (3, "detail", "photo", "close-up: sensor, nameplate, finish"),
    (4, "scale", "photo", "beside hand / pot for size"),
    (5, "packaging", "photo", "box + what's included"),
    (6, "proof", "type", "one honest spec (e.g. tap-to-pair, NFC journal)"),
    (7, "gift", "type", "dedication / occasion angle"),
    (8, "comparison", "type", "us vs bare sensor vs decoy, no invented numbers"),
    (9, "brand", "type", "POW Things mark + collection cross-sell"),
    (10, "spare", "photo", "overflow: alternate angle"),
]


def _parse_copy(copy_path: Path | str) -> dict:
    """Parse an etsy/*.md listing file into front-matter-ish dict."""
    text = Path(copy_path).read_text()
    title = ""
    tags: list[str] = []
    m = __import__("re").search(r"^title:\s*\"(.*)\"$", text, re.M)
    if m:
        title = m.group(1)
    in_tags = False
    for line in text.splitlines():
        if line.strip() == "tags:":
            in_tags = True
            continue
        if in_tags:
            tm = re.match(r"\s*-\s*(.+)$", line)
            if tm:
                tags.append(tm.group(1).strip())
            elif line.strip() and not line.startswith(" "):
                break
    desc = ""
    dm = re.search(r"description: \|(.*?)(?:\ntags:|\Z)", text, re.S)
    if dm:
        desc = dm.group(1).strip()
    return {"title": title, "description": desc, "tags": tags}


def validate_copy(copy_path: Path | str) -> dict:
    """Etsy listing-copy rules, calibrated to the 100-shop study
    (etsysignal/data/ETSY_ANALYSIS.md): 96% use all 13 tags, 74% use
    130+ char titles. Returns {passed, checks}."""
    c = _parse_copy(copy_path)
    checks = {
        "title_le_140": (len(c["title"]) <= 140, f"{len(c['title'])} chars"),
        "title_ge_130": (len(c["title"]) >= 130,
                         f"{len(c['title'])} chars (74% of top shops use 130+)"),
        "tags_eq_13": (len(c["tags"]) == 13,
                       f"{len(c['tags'])} tags (96% use all 13)"),
        "tags_le_20_chars": (all(len(t) <= 20 for t in c["tags"]),
                             "longest: " + (max(c["tags"], key=len) if c["tags"] else "-")),
        "has_description": (len(c["description"]) > 100, f"{len(c['description'])} chars"),
        "no_validated_price_claim": (
            "validated" not in c["description"].lower() or "hypothetical" in c["description"].lower()
            or "target price" in c["description"].lower(),
            "price language"),
        "no_ip_claim": (
            not re.search(r"\bIP\d\d\b", c["description"]),
            "no IP-rating claims"),
    }
    return {"passed": all(v[0] for v in checks.values()),
            "checks": {k: {"ok": v[0], "detail": v[1]} for k, v in checks.items()},
            "copy": c}


def build_packet(segment: str, product: str, copy_path: Path | str,
                 out_dir: Path | str | None = None) -> dict:
    """Assemble a listing packet: slots + validated copy + video slot.

    Photo slots list WHAT to shoot (real photography still required);
    type slots reference renderable cards. Nothing uploads — manual.
    """
    validation = validate_copy(copy_path)
    slots = [{"slot": n, "kind": k, "needs": needs, "status": "copy-ready",
              "detail": detail}
             for n, k, needs, detail in SLOTS]
    packet = {
        "segment": segment, "product": product,
        "copy_file": str(copy_path),
        "copy_valid": validation["passed"],
        "copy_checks": validation["checks"],
        "title": validation["copy"]["title"],
        "tags": validation["copy"]["tags"],
        "slots": slots,
        "video": {"required": "8–12s silent MP4, product in first 3s",
                  "builder": "render/etsy.py:render_video"},
        "upload": "manual: Shop Manager → Listings → Photos and video",
    }
    if out_dir is not None:
        import json
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{product}.packet.json").write_text(
            json.dumps(packet, indent=2))
    return packet
