"""Deterministic IDs — stable entities vs immutable records.

Ported from ographuk/oracle/ids.py. Rules:
- Full hash is identity; TYPE-XXXXXXXX is display only.
- Stable entity: hash(type + namespace + external key), NOT attributes
  (survives renames).
- Immutable record: hash(prefix + canonical payload). Never truncate.
- Canonical JSON: sort_keys, compact separators, UTF-8, allow_nan=False,
  NaN/Inf rejected recursively.
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _assert_finite(obj: Any) -> None:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite float in ID payload")
    elif isinstance(obj, dict):
        for v in obj.values():
            _assert_finite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _assert_finite(v)


def canonical(obj: Any) -> bytes:
    _assert_finite(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entity_id(entity_type: str, namespace: str, external_key: str) -> str:
    """Stable ID for a long-lived entity. Survives attribute renames."""
    et = entity_type.upper()
    return f"{et}:" + _sha256_hex(canonical([et, namespace, external_key]))


def record_id(prefix: str, obj: Any) -> str:
    """Immutable record ID. Full 64-hex — never truncate for identity."""
    return prefix.upper() + ":" + _sha256_hex(canonical(obj))


def record_short(prefix: str, obj: Any) -> str:
    """Display-only short form for filenames/logs. Never use as identity."""
    return prefix.upper() + "-" + _sha256_hex(canonical(obj))[:8].upper()


def content_id_for(hook: str, template: str, segment: str, skin_hash: str,
                   gen_v: int = 1, kind: str = "organic") -> str:
    """Collision-free content ID: segment + skin hash + kind included.

    Replaces the old sha256(hook|template)[:12] which collided across
    segments and silently changed meaning on skin edits. Ads never collide
    with organic builds of the same hook.
    """
    return record_id("AOC", {"hook": hook, "template": template,
                             "segment": segment, "skin_hash": skin_hash,
                             "gen_v": gen_v, "kind": kind})
