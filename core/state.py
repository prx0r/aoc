"""Content state machine — structural human-in-the-loop guarantee.

Stolen from content-management-dashboard. Every path from idea to published
passes through in_review. The AI can prepare, but a human must approve.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ContentStatus(str, Enum):
    IDEA = "idea"
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    MEASURED = "measured"
    REJECTED = "rejected"


# Every possible transition. Proven: everyPathToPublishedPassesReview.
TRANSITIONS: dict[ContentStatus, list[ContentStatus]] = {
    ContentStatus.IDEA: [ContentStatus.DRAFT],
    ContentStatus.DRAFT: [ContentStatus.IN_REVIEW],
    ContentStatus.IN_REVIEW: [ContentStatus.APPROVED, ContentStatus.REJECTED],
    ContentStatus.APPROVED: [ContentStatus.SCHEDULED],
    ContentStatus.SCHEDULED: [ContentStatus.PUBLISHED],
    ContentStatus.PUBLISHED: [ContentStatus.MEASURED],
    ContentStatus.MEASURED: [],
    ContentStatus.REJECTED: [ContentStatus.DRAFT],
}


def check_transition(current: ContentStatus, target: ContentStatus) -> bool:
    """Check if a state transition is allowed."""
    return target in TRANSITIONS.get(current, [])


def transition(content: dict, target: ContentStatus, reason: str = "") -> dict:
    """Apply a transition to a content object. Raises on invalid."""
    current = ContentStatus(content["status"])
    if not check_transition(current, target):
        raise ValueError(f"Invalid transition: {current.value} -> {target.value}")
    content["status"] = target.value
    content["history"].append({
        "from": current.value,
        "to": target.value,
        "reason": reason,
    })
    return content


def create_content(content_id: str, hook: str, slides: list[dict], template: str) -> dict:
    """Create a new content object in IDEA status."""
    return {
        "content_id": content_id,
        "hook": hook,
        "slides": slides,
        "template": template,
        "status": ContentStatus.IDEA.value,
        "history": [],
        "metrics": {},
    }


def _all_paths(current, target, path, found):
    """Enumerate every simple path (graph is small and acyclic enough)."""
    if current == target:
        found.append(list(path))
        return
    for nxt in TRANSITIONS.get(current, []):
        if nxt in path:
            continue
        path.append(nxt)
        _all_paths(nxt, target, path, found)
        path.pop()


def proof_must_haves_review(content: dict | None = None) -> bool:
    """Structural invariant: EVERY path from IDEA to PUBLISHED passes
    through IN_REVIEW — not just that one such path exists.

    Verified by enumerating all simple paths on the transition graph.
    """
    found: list = []
    _all_paths(ContentStatus.IDEA, ContentStatus.PUBLISHED,
               [ContentStatus.IDEA], found)
    return bool(found) and all(
        ContentStatus.IN_REVIEW in p for p in found)
