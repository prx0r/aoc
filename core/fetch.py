"""Fetch results — empty is factual, failure is unknown. Never confuse them.

Ported from ographuk/oracle/sources/fetch_result.py. Wraps every fallible
boundary (CSV loads, Studio imports, LLM calls) so [] from an outage never
equals [] from a genuinely-empty source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class FetchStatus:
    SUCCESS = "SUCCESS"
    SUCCESS_EMPTY = "SUCCESS_EMPTY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class FetchResult:
    status: str
    data: Any = None
    reason: str = ""
    complete: bool = True

    def __post_init__(self):
        # Invariants (ported): PARTIAL/FAILED must never claim completeness.
        if self.status in (FetchStatus.PARTIAL, FetchStatus.FAILED) and self.complete:
            raise ValueError(f"{self.status} with complete=true is contradictory")

    @property
    def is_success(self) -> bool:
        return self.status in (FetchStatus.SUCCESS, FetchStatus.SUCCESS_EMPTY)

    @property
    def has_data(self) -> bool:
        if self.data is None:
            return False
        try:
            return len(self.data) > 0
        except TypeError:
            return True


def fetch_ok(data: Any) -> FetchResult:
    try:
        empty = len(data) == 0
    except TypeError:
        empty = data is None
    if empty:
        return FetchResult(FetchStatus.SUCCESS_EMPTY, data=data,
                           reason="source reachable, genuinely empty")
    return FetchResult(FetchStatus.SUCCESS, data=data)


def fetch_failed(reason: str) -> FetchResult:
    # complete=False: outage is UNKNOWN, never an empty fact.
    return FetchResult(FetchStatus.FAILED, data=None, reason=reason, complete=False)
