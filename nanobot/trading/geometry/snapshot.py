"""Deterministic chart geometry from swings — evidence, not a decision."""

from __future__ import annotations

from typing import Any

from nanobot.trading.geometry.detectors import (
    detect_divergence,
    detect_fair_value_gaps,
    fibonacci_retracement,
)
from nanobot.trading.types import Candle, StructureResult


def build_geometry_snapshot(
    structure: StructureResult,
    candles: list[Candle] | None = None,
) -> dict[str, Any]:
    highs = [s for s in structure.swings if s.type == "high"][-3:]
    lows = [s for s in structure.swings if s.type == "low"][-3:]
    trendlines: list[dict[str, Any]] = []
    if len(highs) >= 2:
        trendlines.append(
            {
                "kind": "resistance",
                "from": highs[-2].price,
                "to": highs[-1].price,
                "state": "falling" if highs[-1].price < highs[-2].price else "rising",
            }
        )
    if len(lows) >= 2:
        trendlines.append(
            {
                "kind": "support",
                "from": lows[-2].price,
                "to": lows[-1].price,
                "state": "rising" if lows[-1].price > lows[-2].price else "falling",
            }
        )
    bars = candles or []
    return {
        "trendlines": trendlines,
        "channels": [],
        "patterns": [],
        "fvg": detect_fair_value_gaps(bars),
        "fibonacci": fibonacci_retracement(structure.swings),
        "divergence": detect_divergence(bars, structure.swings),
        "source": "deterministic_swings",
    }
