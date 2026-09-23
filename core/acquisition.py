"""Acquisition garden — campaign → creative → post → observation → lead →
qualification → conversion. Review workstream E.

Rules (peer review):
- Snapshots append; CURRENT totals come from the latest valid observation.
- Intervals derive from consecutive snapshots. Reimports never duplicate
  (UNIQUE post_id/observed_at/metric/import_id).
- Leads and sales join to campaigns only where attribution exists;
  unattributed conversions are reported separately, never guessed.
- Enquiry ≠ qualified conversation: qualification is an independent event.
- Funnel: impressions → profile visits → clicks → DMs → waitlist regs →
  qualified conversations → bookings → paid → refunds → 7-day active use.
"""

from __future__ import annotations

from core.store import log_event, session


def ingest_observation(post_id: str, observed_at: str, metric: str,
                       value: float | None, source: str, import_id: str) -> bool:
    """Idempotent ingest. Returns True if new, False if duplicate."""
    with session() as db:
        cur = db.execute(
            """INSERT OR IGNORE INTO observations
               (post_id, observed_at, metric, value, source, import_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (post_id, observed_at, metric, value, source, import_id))
        return cur.rowcount == 1


def current_totals(post_id: str) -> dict:
    """Latest valid observation per metric = current totals."""
    with session() as db:
        rows = db.execute(
            """SELECT metric, value FROM observations o
               WHERE post_id = ? AND observed_at = (
                   SELECT MAX(observed_at) FROM observations
                   WHERE post_id = o.post_id AND metric = o.metric
                     AND value IS NOT NULL)""",
            (post_id,)).fetchall()
        return {r["metric"]: r["value"] for r in rows}


def intervals(post_id: str, metric: str) -> list[dict]:
    """Consecutive-snapshot interval changes for one metric."""
    with session() as db:
        rows = db.execute(
            """SELECT observed_at, value FROM observations
               WHERE post_id = ? AND metric = ? AND value IS NOT NULL
               ORDER BY observed_at""",
            (post_id, metric)).fetchall()
    out = []
    prev = None
    for r in rows:
        if prev is not None:
            out.append({"from": prev["observed_at"], "to": r["observed_at"],
                        "delta": r["value"] - prev["value"]})
        prev = r
    return out


def record_lead(lead_id: str, source: str, campaign_id: str = "",
                creative_id: str = "", permission_status: str = "unknown",
                permission_ref: str = "", contact_ref: str = "") -> None:
    """A lead is an enquiry. Qualification is separate (record_qualification)."""
    with session() as db:
        db.execute(
            """INSERT OR REPLACE INTO leads
               (lead_id, acquired_at, source, campaign_id, creative_id,
                permission_status, permission_ref, contact_ref)
               VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)""",
            (lead_id, source, campaign_id, creative_id,
             permission_status, permission_ref, contact_ref))
        log_event(db, "lead", "", "system", {"lead_id": lead_id, "source": source})


def record_qualification(lead_id: str, qualified: bool,
                         is_owner_manager: bool | None = None,
                         business_type: str = "", stated_need: str = "") -> None:
    """Independent qualification event. Enquiry ≠ qualified conversation."""
    with session() as db:
        db.execute(
            """INSERT OR REPLACE INTO qualifications
               (lead_id, qualified_at, is_owner_manager, business_type,
                stated_need, qualified)
               VALUES (?, datetime('now'), ?, ?, ?, ?)""",
            (lead_id, is_owner_manager, business_type, stated_need, qualified))
        log_event(db, "qualified" if qualified else "disqualified",
                  "", "system", {"lead_id": lead_id})


def record_conversion(lead_id: str, amount_gbp: float | None = None,
                      booked_at: str = "", paid_at: str = "",
                      refunded_at: str = "", active_7d: bool | None = None) -> None:
    with session() as db:
        db.execute(
            """INSERT OR REPLACE INTO conversions
               (lead_id, booked_at, paid_at, amount_gbp, refunded_at, active_7d)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lead_id, booked_at, paid_at, amount_gbp, refunded_at, active_7d))
        log_event(db, "conversion", "", "system",
                  {"lead_id": lead_id, "amount_gbp": amount_gbp})


def funnel(campaign_id: str = "") -> dict:
    """Funnel counts, attributed where possible, unattributed reported apart."""
    with session() as db:
        filt = "WHERE campaign_id = ?" if campaign_id else ""
        args = (campaign_id,) if campaign_id else ()
        leads = db.execute(
            f"SELECT COUNT(*) c FROM leads {filt}", args).fetchone()["c"]
        if campaign_id:
            quals = db.execute(
                """SELECT COUNT(*) c FROM qualifications q JOIN leads l
                   ON q.lead_id = l.lead_id
                   WHERE q.qualified = 1 AND l.campaign_id = ?""",
                (campaign_id,)).fetchone()["c"]
            conv = db.execute(
                """SELECT COUNT(*) c, COALESCE(SUM(c2.amount_gbp), 0) s
                   FROM conversions c2 JOIN leads l ON c2.lead_id = l.lead_id
                   WHERE l.campaign_id = ? AND c2.paid_at != ''""",
                (campaign_id,)).fetchone()
            unattributed = db.execute(
                """SELECT COUNT(*) c FROM conversions c2 LEFT JOIN leads l
                   ON c2.lead_id = l.lead_id
                   WHERE (l.campaign_id IS NULL OR l.campaign_id = '')
                   AND c2.paid_at != ''""").fetchone()["c"]
        else:
            quals = db.execute(
                "SELECT COUNT(*) c FROM qualifications WHERE qualified = 1").fetchone()["c"]
            conv = db.execute(
                "SELECT COUNT(*) c, COALESCE(SUM(amount_gbp), 0) s FROM conversions WHERE paid_at != ''").fetchone()
            unattributed = 0
        return {"leads": leads, "qualified": quals,
                "paid": conv["c"], "revenue_gbp": conv["s"],
                "unattributed_paid": unattributed}
