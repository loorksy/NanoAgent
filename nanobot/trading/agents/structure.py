"""Structure agent — swings, trend, BOS events."""

from __future__ import annotations

from nanobot.trading.geometry.detectors import (
    detect_structure_events,
    find_swings,
    infer_trend,
    support_resistance,
)
from nanobot.trading.types import AgentMarketContext, StructureResult


def run_structure_agent(market: AgentMarketContext) -> StructureResult:
    swings = find_swings(market.candles)
    support, resistance = support_resistance(swings, market.last_close)
    events = detect_structure_events(swings, market.candles)
    return StructureResult(
        trend=infer_trend(swings),
        swings=swings,
        support=support,
        resistance=resistance,
        structure_events=events,
        latest_structure_event=events[-1] if events else None,
    )
