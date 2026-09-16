"""G2/G3 plan checks against liquidity and supply/demand maps."""

from __future__ import annotations

from nanobot.trading.i18n import tr
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan, LiquidityResult, SupplyDemandResult


def evaluate_liquidity_alignment(
    plan: EntryPlan,
    liquidity: LiquidityResult,
    atr: float,
    *,
    locale: str = "en",
) -> tuple[str, str]:
    """Return gate status and localized reason (pass or veto)."""
    proximity = max(atr * live().LIQUIDITY_PROXIMITY_ATR, 0.01)
    entry = plan.entry

    if plan.direction == "buy":
        overhead = liquidity.nearest_buy_side
        if overhead is not None:
            distance = overhead.price - entry
            if 0 <= distance <= proximity:
                return (
                    "veto",
                    tr("gate.buy_near_liquidity", locale, distance=f"{distance:.2f}"),
                )
        sweep = liquidity.latest_sweep
        if sweep and sweep.side == "buy_side" and sweep.close_back_inside:
            return "veto", tr("gate.buy_against_sweep", locale)
    else:
        below = liquidity.nearest_sell_side
        if below is not None:
            distance = entry - below.price
            if 0 <= distance <= proximity:
                return (
                    "veto",
                    tr("gate.sell_near_liquidity", locale, distance=f"{distance:.2f}"),
                )
        sweep = liquidity.latest_sweep
        if sweep and sweep.side == "sell_side" and sweep.close_back_inside:
            return "veto", tr("gate.sell_against_sweep", locale)

    return "pass", ""


def evaluate_supply_demand_alignment(
    plan: EntryPlan,
    supply_demand: SupplyDemandResult,
    *,
    locale: str = "en",
) -> tuple[str, str]:
    """Return gate status and localized reason (pass or veto)."""
    entry = plan.entry
    for zone in supply_demand.zones:
        if zone.low <= entry <= zone.high:
            if plan.direction == "buy" and zone.type == "supply":
                return "veto", tr("gate.buy_in_supply", locale)
            if plan.direction == "sell" and zone.type == "demand":
                return "veto", tr("gate.sell_in_demand", locale)
    return "pass", ""
