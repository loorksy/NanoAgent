"""Build chart drawing plan from analysis results."""

from __future__ import annotations

from nanobot.trading.types import (
    ChartDrawing,
    FinalDecisionResult,
    StructureResult,
    SupplyDemandResult,
)


def build_drawing_plan(
    structure: StructureResult,
    supply_demand: SupplyDemandResult,
    decision: FinalDecisionResult,
) -> list[ChartDrawing]:
    drawings: list[ChartDrawing] = []
    for level in structure.support[:2]:
        drawings.append(
            ChartDrawing(
                type="price_line",
                confidence=70,
                label="Support",
                color="#22c55e",
                semantic_role="support",
                points=[{"time": float(level.time), "price": level.price}],
            )
        )
    for level in structure.resistance[:2]:
        drawings.append(
            ChartDrawing(
                type="price_line",
                confidence=70,
                label="Resistance",
                color="#ef4444",
                semantic_role="resistance",
                points=[{"time": float(level.time), "price": level.price}],
            )
        )
    if supply_demand.nearest_demand:
        z = supply_demand.nearest_demand
        drawings.append(
            ChartDrawing(
                type="demand_zone",
                confidence=75,
                label="Demand",
                color="#22c55e",
                fill=True,
                semantic_role="demand_zone",
                points=[
                    {"time": float(z.time), "price": z.low},
                    {"time": float(z.time), "price": z.high},
                ],
            )
        )
    rec = decision.recommendation
    if rec.action in ("buy", "sell") and rec.entry and rec.stop_loss:
        drawings.append(
            ChartDrawing(
                type="decision_zone",
                confidence=80,
                label="Invalidation",
                color="#f59e0b",
                semantic_role="invalidation",
                points=[
                    {"time": float(rec.anchor_time or 0), "price": rec.stop_loss},
                ],
            )
        )
    return drawings[:9]
