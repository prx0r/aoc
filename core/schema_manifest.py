"""Schema manifest — one source of truth for every record shape.

Ported from ographuk/oracle/schema_manifest.py. Schemas are implicit dicts
scattered across state/proof/carousel/receipt/analytics; this file lists
them centrally so drift is caught by test_schema_parity instead of by users.
"""

from __future__ import annotations

SCHEMAS: dict[str, dict[str, str]] = {
    # core/state.py:create_content
    "Content": {
        "content_id": "str", "hook": "str", "slides": "list",
        "template": "str", "status": "str", "history": "list", "metrics": "dict",
    },
    # core/carousel.py:plan
    "Plan": {
        "hook": "str", "template": "str", "audience": "str", "cta": "str",
        "slides": "list", "segment": "str", "kind": "str", "skin_hash": "str",
        "content_id": "str", "created_at": "str",
    },
    # core/proof.py:Proof.to_dict
    "Proof": {
        "proof_id": "str", "kind": "str", "source": "str", "subject": "str",
        "claims": "list", "evidence_refs": "list", "observed_at": "str",
        "lineage_root": "str",
    },
    # core/carousel.py:render manifest
    "Manifest": {
        "content_id": "str", "hook": "str", "template": "str",
        "slides": "list", "sha256": "dict",
    },
    # core/receipt.py:append_receipt
    "Receipt": {
        "receipt_id": "str", "prev": "str", "event": "str",
        "at": "str", "data": "dict",
    },
    # core/gates.py:run_gates result
    "Gates": {
        "passed": "bool", "gates": "dict",
    },
    # core/analytics.py:record_snapshot row
    "Snapshot": {
        "at": "str", "post_url": "str", "content_id": "str",
        "source": "str", "metrics": "dict",
    },
    # core/personalize.py:variant_spec
    "Variant": {
        "business": "str", "company_number": "str", "area": "str",
        "segment": "str", "template": "str", "hook": "str",
        "score": "dict", "status": "str", "source": "str",
    },
}


def check_parity(records: dict[str, dict]) -> dict:
    """Compare live records against the manifest.

    Returns {"missing": {schema: [keys]}, "extra": {schema: [keys]}}.
    Empty means parity.
    """
    missing: dict[str, list] = {}
    extra: dict[str, list] = {}
    for name, declared in SCHEMAS.items():
        actual = records.get(name, {})
        declared_keys = set(declared)
        actual_keys = set(actual)
        m = sorted(declared_keys - actual_keys)
        e = sorted(actual_keys - declared_keys)
        if m:
            missing[name] = m
        if e:
            extra[name] = e
    return {"missing": missing, "extra": extra}
