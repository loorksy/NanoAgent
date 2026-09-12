"""Liquidity agent — equal highs/lows and sweeps."""

from __future__ import annotations

from nanobot.trading.geometry.detectors import detect_sweeps, find_equal_levels, find_swings
from nanobot.trading.types import AgentMarketContext, LiquidityResult, PriceLevel


def run_liquidity_agent(market: AgentMarketContext) -> LiquidityResult:
    swings = find_swings(market.candles)
    eq_highs, eq_lows = find_equal_levels(swings)
    sweeps = detect_sweeps(market.candles, eq_highs, eq_lows)
    nearest_buy = eq_highs[0] if eq_highs else None
    nearest_sell = eq_lows[0] if eq_lows else None
    if not nearest_buy and market.last_close:
        highs = [s for s in swings if s.type == "high" and s.price > market.last_close]
        if highs:
            nearest_buy = PriceLevel(price=highs[-1].price, time=highs[-1].time)
    if not nearest_sell and market.last_close:
        lows = [s for s in swings if s.type == "low" and s.price < market.last_close]
        if lows:
            nearest_sell = PriceLevel(price=lows[-1].price, time=lows[-1].time)
    return LiquidityResult(
        equal_highs=eq_highs,
        equal_lows=eq_lows,
        nearest_buy_side=nearest_buy,
        nearest_sell_side=nearest_sell,
        sweeps=sweeps,
        latest_sweep=sweeps[-1] if sweeps else None,
    )
