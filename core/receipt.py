"""Receipt chain — hash-chained content log. Stolen from /content + ai-ugc-slideshows.

Every carousel write appends a receipt. Tampering breaks the chain.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _hash(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def append_receipt(receipts_path: Path | str, event: str, data: dict) -> dict:
    receipts_path = Path(receipts_path)
    receipts_path.parent.mkdir(parents=True, exist_ok=True)

    prev = "GENESIS"
    if receipts_path.exists():
        with open(receipts_path) as f:
            lines = [ln for ln in f if ln.strip()]
            if lines:
                prev = json.loads(lines[-1]).get("receipt_id", "GENESIS")

    receipt = {
        "receipt_id": "",
        "prev": prev,
        "event": event,
        "at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    receipt["receipt_id"] = _hash({k: v for k, v in receipt.items() if k != "receipt_id"})
    with open(receipts_path, "a") as f:
        f.write(json.dumps(receipt) + "\n")
    return receipt


def verify_chain(receipts_path: Path | str) -> tuple[bool, str]:
    """Verify hash chain. Returns (ok, message)."""
    p = Path(receipts_path)
    if not p.exists():
        return True, "empty chain"
    prev = "GENESIS"
    with open(p) as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line)
            if r.get("prev") != prev:
                return False, f"break at line {i}: prev mismatch"
            expect = _hash({k: v for k, v in r.items() if k != "receipt_id"})
            if expect != r.get("receipt_id"):
                return False, f"break at line {i}: hash mismatch"
            prev = r["receipt_id"]
    return True, f"ok, head={prev}"
