"""G2/G3 plan checks against liquidity and supply/demand maps."""

from __future__ import annotations

from nanobot.trading.types import EntryPlan, LiquidityResult, SupplyDemandResult

LIQUIDITY_PROXIMITY_ATR = 0.3


def evaluate_liquidity_alignment(
    plan: EntryPlan,
    liquidity: LiquidityResult,
    atr: float,
) -> tuple[str, str]:
    """Return gate status and Arabic reason (pass or veto)."""
    proximity = max(atr * LIQUIDITY_PROXIMITY_ATR, 0.01)
    entry = plan.entry

    if plan.direction == "buy":
        overhead = liquidity.nearest_buy_side
        if overhead is not None:
            distance = overhead.price - entry
            if 0 <= distance <= proximity:
                return (
                    "veto",
                    f"الدخول شراء قريب جداً من سيولة علوية ({distance:.2f})",
                )
        sweep = liquidity.latest_sweep
        if sweep and sweep.side == "buy_side" and sweep.close_back_inside:
            return "veto", "شراء عكس sweep سيولة علوية حديث"
    else:
        below = liquidity.nearest_sell_side
        if below is not None:
            distance = entry - below.price
            if 0 <= distance <= proximity:
                return (
                    "veto",
                    f"الدخول بيع قريب جداً من سيولة سفلية ({distance:.2f})",
                )
        sweep = liquidity.latest_sweep
        if sweep and sweep.side == "sell_side" and sweep.close_back_inside:
            return "veto", "بيع عكس sweep سيولة سفلية حديث"

    return "pass", ""


def evaluate_supply_demand_alignment(
    plan: EntryPlan,
    supply_demand: SupplyDemandResult,
) -> tuple[str, str]:
    """Return gate status and Arabic reason (pass or veto)."""
    entry = plan.entry
    for zone in supply_demand.zones:
        if zone.low <= entry <= zone.high:
            if plan.direction == "buy" and zone.type == "supply":
                return "veto", "دخول شراء داخل منطقة عرض"
            if plan.direction == "sell" and zone.type == "demand":
                return "veto", "دخول بيع داخل منطقة طلب"
    return "pass", ""
