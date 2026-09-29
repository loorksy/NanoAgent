"""Detect a gold buy/sell question. The kernel tool performs the review."""

from __future__ import annotations

import re

_DECISION = re.compile(
    r"هل\s+أشتري|هل\s+اشتري|هل\s+أبيع|هل\s+ابيع|"
    r"should i buy|should i sell|"
    r"أشتري الذهب|اشتري الذهب|أبيع الذهب|ابيع الذهب",
    re.IGNORECASE,
)


def is_gold_decision_question(text: str) -> bool:
    return bool(_DECISION.search(text or ""))
