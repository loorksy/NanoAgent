"""Build chart drawing plan: S/R, zones, and Lonora scenario paths."""

from __future__ import annotations

from nanobot.trading.types import (
    AgentMarketContext,
    ChartDrawing,
    FinalDecisionResult,
    ScenarioWaypoint,
    StructureResult,
    SupplyDemandResult,
)

_MAX_OBJECTS = 12


def _path_points(
    waypoints: list[ScenarioWaypoint],
    *,
    start_price: float,
    start_time: float,
    bar_ms: int,
) -> list[dict[str, float]]:
    points = [{"time": start_time, "price": start_price}]
    last_time = start_time
    for wp in waypoints:
        t = start_time + wp.bars_ahead * bar_ms
        if t <= last_time:
            t = last_time + bar_ms
        points.append({"time": float(t), "price": wp.price})
        last_time = t
    return points


def build_drawing_plan(
    structure: StructureResult,
    supply_demand: SupplyDemandResult,
    decision: FinalDecisionResult,
    market: AgentMarketContext | None = None,
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
    start_price = rec.entry or (market.last_close if market else 0.0)
    start_time = float(rec.anchor_time or (market.candles[-1].time_ms if market and market.candles else 0))
    bar_ms = 15 * 60 * 1000
    if rec.scenario_path and start_price:
        drawings.append(
            ChartDrawing(
                type="forecast_path",
                confidence=80,
                label="Scenario",
                color="#38bdf8",
                semantic_role="scenario_path",
                points=_path_points(
                    rec.scenario_path,
                    start_price=start_price,
                    start_time=start_time,
                    bar_ms=bar_ms,
                ),
                meta={"role": "primary"},
            )
        )
    if rec.alternative_scenario_path and start_price:
        drawings.append(
            ChartDrawing(
                type="forecast_path",
                confidence=70,
                label="Alternative",
                color="#f97316",
                style="dashed",
                semantic_role="alternative_scenario_path",
                points=_path_points(
                    rec.alternative_scenario_path,
                    start_price=start_price,
                    start_time=start_time,
                    bar_ms=bar_ms,
                ),
                meta={"role": "alternative"},
            )
        )
    if rec.action in ("buy", "sell") and rec.entry and rec.stop_loss:
        drawings.append(
            ChartDrawing(
                type="decision_zone",
                confidence=80,
                label="Invalidation",
                color="#f59e0b",
                semantic_role="invalidation",
                points=[
                    {"time": float(rec.anchor_time or start_time), "price": rec.stop_loss},
                ],
            )
        )
    return drawings[:_MAX_OBJECTS]
