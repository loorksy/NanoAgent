"""Supply & demand zones agent."""

from __future__ import annotations

from nanobot.trading.geometry.detectors import build_supply_demand_zones
from nanobot.trading.types import AgentMarketContext, SupplyDemandResult, SupplyDemandZone


def run_supply_demand_agent(market: AgentMarketContext) -> SupplyDemandResult:
    zones = build_supply_demand_zones(market.candles, market.atr)
    nearest_demand = next((z for z in zones if z.type == "demand"), None)
    nearest_supply = next((z for z in zones if z.type == "supply"), None)
    if not nearest_demand and market.last_close:
        for z in zones:
            if z.high < market.last_close:
                nearest_demand = z
                break
    if not nearest_supply and market.last_close:
        for z in zones:
            if z.low > market.last_close:
                nearest_supply = z
                break
    return SupplyDemandResult(
        zones=zones,
        nearest_demand=nearest_demand,
        nearest_supply=nearest_supply,
    )
