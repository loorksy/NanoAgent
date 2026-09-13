"""Route user messages to gold trading modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanobot.trading.operator_keywords import (
    _ANALYSIS_PATTERNS,
    _CHART_IMAGE_PATTERNS,
    _GOLD_PATTERNS,
    _PRESET_BY_KEYWORD,
    _PRICE_PATTERNS,
    _RECOMMEND_PATTERNS,
    _TEAM_PATTERNS,
)

IntentKind = Literal[
    "price_query",
    "chart_image",
    "gold_analysis",
    "recommendation",
    "team_swarm",
    "general_chat",
]


@dataclass(frozen=True)
class RoutedIntent:
    kind: IntentKind
    confidence: float
    reason: str


def resolve_team_preset(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    for pattern, preset in _PRESET_BY_KEYWORD:
        if pattern.search(text):
            return preset
    return None


def route_intent(message: str) -> RoutedIntent:
    text = (message or "").strip()
    if not text:
        return RoutedIntent("general_chat", 0.0, "empty")

    mentions_gold = any(p.search(text) for p in _GOLD_PATTERNS)
    if any(p.search(text) for p in _CHART_IMAGE_PATTERNS):
        return RoutedIntent(
            "chart_image",
            0.92 if mentions_gold else 0.8,
            "chart image keywords",
        )
    if any(p.search(text) for p in _TEAM_PATTERNS):
        return RoutedIntent("team_swarm", 0.9 if mentions_gold else 0.75, "team preset keywords")
    if any(p.search(text) for p in _RECOMMEND_PATTERNS):
        return RoutedIntent("recommendation", 0.9 if mentions_gold else 0.85, "recommendation keywords")
    if any(p.search(text) for p in _ANALYSIS_PATTERNS):
        return RoutedIntent("gold_analysis", 0.9 if mentions_gold else 0.85, "analysis keywords")
    if any(p.search(text) for p in _PRICE_PATTERNS):
        return RoutedIntent("price_query", 0.85 if mentions_gold else 0.6, "price keywords")
    if mentions_gold:
        return RoutedIntent("gold_analysis", 0.65, "gold mention")
    return RoutedIntent("general_chat", 0.5, "default")
