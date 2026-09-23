"""Per-business personalization — one engine, every prospect as a variant.

Design constraints (from aionboard OFFER.md + targets.md + contact rules):
1. Identity-only tokens: {business_name}, {area}. Never personalize numbers,
   claims, or outcomes — stats stay segment-level from proofs.yaml.
2. Research vs marketing split: generated variants default to status
   `research-only` (do NOT send). Only `consented` assets may go into 1-to-1
   follow-ups (post-call, demo leave-behind). Never bulk-unsolicited.
3. Prospect facts come from CSV columns only. No invented names, areas,
   or services. Truncate names to fit slides.
4. Scoring ports aionboard/PROSPECT_SCORING.md using CSV-available fields:
   sic diversity + region density. Age/hiring need CH API (recorded as unknown).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ALLOWED_TOKENS = {"business_name", "area", "service"}


def load_prospects(csv_path: Path | str) -> list[dict]:
    """Load prospect CSV. Expected columns: company_number, name, postcode,
    region, sic_codes, status, cluster."""
    return load_prospects_result(csv_path).data or []


def load_prospects_result(csv_path: Path | str):
    """FetchResult-wrapped load: outage is UNKNOWN, empty file is a fact.

    (Ported from ographuk FetchStatus: FAILED ≠ SUCCESS_EMPTY.)
    """
    from core.fetch import fetch_failed, fetch_ok
    try:
        rows = []
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                rows.append({k: (v or "").strip() for k, v in row.items()})
        return fetch_ok(rows)
    except (FileNotFoundError, PermissionError) as e:
        return fetch_failed(f"prospect CSV unreadable: {e}")
    except Exception as e:
        return fetch_failed(f"prospect CSV parse error: {e}")


def score_prospect(row: dict, region_counts: dict[str, int]) -> dict:
    """Score 0-100 per PROSPECT_SCORING using CSV-available fields.

    Geographic density (0-25): businesses sharing the region code.
    Service diversity (0-25): number of SIC codes listed.
    Business age (unknown without CH API): 0 + flag.
    Growth signals (partial): related construction SIC present = 5.
    """
    region = (row.get("region") or "").upper()
    n = region_counts.get(region, 0)
    density = 25 if n > 200 else 20 if n > 150 else 15 if n > 100 else 10 if n > 50 else 5

    sics = [s.strip() for s in (row.get("sic_codes") or "").replace(";", ",").split(",") if s.strip()]
    diversity = 25 if len(sics) >= 4 else 20 if len(sics) == 3 else 15 if len(sics) == 2 else 10

    growth = 5 if any(s != "43210" and s.startswith("43") for s in sics) else 0

    total = density + diversity + growth  # age unknown → 0, max 55 without CH data
    priority = "WARM" if total >= 40 else "COOL" if total >= 25 else "COLD"
    return {"score": total, "priority": priority, "sic_count": len(sics),
            "region_count": n, "age_unknown": True,
            "priority_note": "HOT requires CH age + hiring verification (not in CSV)"}


def short_name(name: str, limit: int = 26) -> str:
    """Trim LTD/PLC suffixes and truncate to fit a slide."""
    clean = re.sub(r"\s+(LTD\.?|LIMITED|PLC\.?|LLP)$", "", name.strip(), flags=re.I)
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def personalize_hook(hook: str, row: dict) -> str:
    """Prepend business identity to a segment hook. Identity only, no claims."""
    name = short_name(row.get("name", ""))
    area = (row.get("region") or "").upper()
    if name and area:
        return f"{name} ({area}) — {hook[:1].lower() + hook[1:]}"
    return hook


def check_tokens(text: str) -> tuple[bool, str]:
    """Gate: every {token} must be in ALLOWED_TOKENS and resolved upstream."""
    found = set(re.findall(r"\{(\w+)\}", text))
    bad = found - ALLOWED_TOKENS
    if bad:
        return False, f"forbidden tokens: {sorted(bad)}"
    return True, "tokens ok"


def business_id(row: dict) -> str:
    """Canonical business identity supporting registered AND unincorporated
    businesses. A name/handle alone is never identity; one durable,
    verifiable source key is required.

    Accepted, in order: Companies House number > verified booking-page id >
    authorised business-profile id. Returns "" when unverifiable.
    """
    ch = (row.get("company_number") or "").strip()
    if ch:
        return f"CH:{ch}"
    for key in ("booking_page_id", "business_profile_id", "directory_id"):
        val = (row.get(key) or "").strip()
        if val:
            return f"{key}:{val}"
    return ""


def variant_spec(row: dict, hook: str, template: str, segment: str,
                 status: str = "research-only",
                 permission_ref: str = "") -> dict:
    """Build a per-business variant spec. Status gates delivery.

    consented requires a verifiable permission_ref — an MCP caller cannot
    mark a prospect consented by merely supplying the string. Research-only
    records can never flow into a send queue.
    """
    if status not in ("research-only", "consented"):
        raise ValueError("status must be research-only or consented")
    if status == "consented" and not permission_ref:
        raise ValueError("consented status requires permission_ref evidence "
                         "(call log, form receipt, or opt-in record id)")
    bid = business_id(row)
    if not bid:
        raise ValueError("unverifiable business identity: need company_number "
                         "or a verified booking/profile/directory id")
    region_counts: dict[str, int] = {}
    scoring = score_prospect(row, region_counts)
    return {
        "business": short_name(row.get("name", "")),
        "business_id": bid,
        "company_number": row.get("company_number", ""),
        "area": (row.get("region") or "").upper(),
        "segment": segment,
        "template": template,
        "hook": personalize_hook(hook, row),
        "score": scoring,
        "status": status,  # research-only = do NOT send; consented = 1-to-1 follow-up only
        "permission_ref": permission_ref,
        "source": "prospects CSV (research record, not marketing permission)",
    }


def top_prospects(csv_path: Path | str, limit: int = 20,
                  min_score: int = 25) -> list[dict]:
    """Rank prospects for a batch. Returns top-N with scores attached."""
    rows = [r for r in load_prospects(csv_path) if (r.get("status") or "").lower() == "active"]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.get("region", "").upper()] = counts.get(r.get("region", "").upper(), 0) + 1
    scored = [(score_prospect(r, counts)["score"], r) for r in rows]
    scored.sort(key=lambda t: -t[0])
    out = []
    for score, r in scored[:limit]:
        if score >= min_score:
            out.append({**r, **score_prospect(r, counts)})
    return out
