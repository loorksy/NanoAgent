"""Deterministic chart geometry from swings — evidence, not a decision."""

from __future__ import annotations

from typing import Any

from nanobot.trading.types import StructureResult


def build_geometry_snapshot(structure: StructureResult) -> dict[str, Any]:
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
    return {
        "trendlines": trendlines,
        "channels": [],
        "patterns": [],
        "source": "deterministic_swings",
    }
