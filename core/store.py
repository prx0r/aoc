"""ContentStore — SQLite-backed lifecycle state + acquisition garden.

Replaces scattered JSONL reads with transactional writes. Tables:
- content_state: one row per creative, strict lifecycle transitions
- events: append-only event log (mirrors receipts JSONL format)
- campaigns, creatives, posts, observations: acquisition chain
- leads, qualifications, conversions: funnel with consent + attribution
- experiments: variable changed, comparison group, outcome

Unknown=null throughout: missing metrics are NULL, never 0.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import os

DB_PATH = Path(__file__).parent.parent / "store" / "aoc.db"


def db_path() -> Path:
    """Overridable via AOC_DB (tests point it at tmp dirs)."""
    return Path(os.environ.get("AOC_DB", str(DB_PATH)))

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_state (
    content_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    segment TEXT NOT NULL,
    template TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'organic',
    status TEXT NOT NULL DEFAULT 'draft',
    actor TEXT NOT NULL DEFAULT 'system',
    creative_hash TEXT,
    zip_sha256 TEXT,
    caption TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    event TEXT NOT NULL,
    content_id TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL DEFAULT 'system',
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_content ON events(content_id);
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    segment TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    offer_version INTEGER NOT NULL,
    hypothesis TEXT NOT NULL DEFAULT '',
    budget_gbp REAL,
    channel TEXT NOT NULL DEFAULT 'tiktok',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS creatives (
    creative_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL DEFAULT '',
    content_id TEXT NOT NULL,
    script_hash TEXT NOT NULL,
    cta TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    renderer TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(content_id)
);
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    creative_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    account TEXT NOT NULL,
    platform_post_id TEXT NOT NULL DEFAULT '',
    post_url TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    source TEXT NOT NULL,
    import_id TEXT NOT NULL,
    UNIQUE(post_id, observed_at, metric, import_id)
);
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    acquired_at TEXT NOT NULL,
    source TEXT NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT '',
    creative_id TEXT NOT NULL DEFAULT '',
    permission_status TEXT NOT NULL DEFAULT 'unknown',
    permission_ref TEXT NOT NULL DEFAULT '',
    contact_ref TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS qualifications (
    lead_id TEXT PRIMARY KEY,
    qualified_at TEXT NOT NULL,
    is_owner_manager INTEGER,
    business_type TEXT NOT NULL DEFAULT '',
    stated_need TEXT NOT NULL DEFAULT '',
    qualified BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS conversions (
    lead_id TEXT PRIMARY KEY,
    booked_at TEXT NOT NULL DEFAULT '',
    paid_at TEXT NOT NULL DEFAULT '',
    amount_gbp REAL,
    refunded_at TEXT NOT NULL DEFAULT '',
    active_7d BOOLEAN
);
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    variable TEXT NOT NULL,
    group_a TEXT NOT NULL DEFAULT '',
    group_b TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS suppression (
    business_id TEXT PRIMARY KEY,
    withdrawn_at TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'all'
);
"""

# draft → validated → rendered → in_review → approved → ready/manual flows
TRANSITIONS: dict[str, set[str]] = {
    "draft": {"validated", "rejected"},
    "validated": {"rendered", "rejected"},
    "rendered": {"in_review", "rejected"},
    "in_review": {"approved", "rejected"},
    "rejected": {"draft"},
    "approved": {"ready_for_manual_post"},
    "ready_for_manual_post": {"published_confirmed", "approved"},
    "published_confirmed": {"measured"},
    "measured": set(),
}


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path) if path is not None else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


from contextlib import contextmanager


@contextmanager
def session(path: Path | str | None = None):
    """One transactional session. Usage: with session() as db: ..."""
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(conn: sqlite3.Connection, event: str, content_id: str = "",
              actor: str = "system", data: dict | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO events (at, event, content_id, actor, data) VALUES (?, ?, ?, ?, ?)",
        (now(), event, content_id, actor, json.dumps(data or {}, default=str)))
    conn.commit()
    return cur.lastrowid


def set_status(conn: sqlite3.Connection, content_id: str, target: str,
               actor: str = "system", **fields) -> None:
    """Transition with predecessor + actor validation. Raises on violation."""
    row = conn.execute("SELECT status FROM content_state WHERE content_id = ?",
                       (content_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown content_id: {content_id[:24]}")
    current = row["status"]
    if current == target:
        return  # idempotent: parallel workers re-asserting state is fine
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"illegal transition {current} -> {target}")
    if target in ("approved", "ready_for_manual_post", "published_confirmed") and actor == "system":
        raise ValueError(f"{target} requires a human actor, not system")
    updates = ", ".join([f"{k} = ?" for k in fields] + ["status = ?", "actor = ?", "updated_at = ?"])
    conn.execute(f"UPDATE content_state SET {updates} WHERE content_id = ?",
                 (*fields.values(), target, actor, now(), content_id))
    log_event(conn, f"status:{target}", content_id, actor, dict(fields))
    conn.commit()


def upsert_content(conn: sqlite3.Connection, content_id: str, experiment_id: str,
                   segment: str, template: str, kind: str = "organic") -> None:
    conn.execute(
        """INSERT INTO content_state
           (content_id, experiment_id, segment, template, kind, status, actor, updated_at)
           VALUES (?, ?, ?, ?, ?, 'draft', 'system', ?)
           ON CONFLICT(content_id) DO NOTHING""",
        (content_id, experiment_id, segment, template, kind, now()))
    conn.commit()
