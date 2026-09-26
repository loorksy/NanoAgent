"""Learning-loop evidence (R10). A past loss is a weighted note, not a gate."""

from __future__ import annotations


def lesson_from_loss(*, setup: str, reason: str, side: str) -> dict[str, object]:
    return {
        "kind": "lessons",
        "setup": setup,
        "reason": reason,
        "side": side,
        "weight": 1,
        "blocks": False,
        "notice_key": "lesson.evidence",
    }
