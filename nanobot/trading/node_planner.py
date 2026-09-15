"""Select evidence node subsets for analysis turns (Phase K)."""

from __future__ import annotations

from nanobot.trading.evidence.node_sets import (
    ANALYSIS_WITHOUT_VISUAL_NODES,
    FULL_ANALYSIS_NODES,
)
from nanobot.trading.intent_router import RoutedIntent
from nanobot.trading.operator_keywords import wants_quick_analysis


def select_analysis_nodes(message: str, intent: RoutedIntent) -> tuple[str, ...]:
    """Pick evidence nodes for a fresh analysis turn."""
    if wants_quick_analysis(message):
        return ANALYSIS_WITHOUT_VISUAL_NODES
    return FULL_ANALYSIS_NODES
