"""Multi-timeframe bias agent."""

from __future__ import annotations

from nanobot.trading.agents.structure import run_structure_agent
from nanobot.trading.geometry.detectors import find_swings, infer_trend
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.market_context import build_agent_market_context
from nanobot.trading.types import AgentMarketContext, Bias, MultiTimeframeResult


def _trend_to_bias(trend: str) -> Bias:
    if trend == "uptrend":
        return "bullish"
    if trend == "downtrend":
        return "bearish"
    if trend == "range":
        return "neutral"
    return "unknown"


def _bias_from_context(market: AgentMarketContext) -> Bias:
    if not market.candles:
        return "unknown"
    return _trend_to_bias(infer_trend(find_swings(market.candles)))


def run_multi_timeframe_agent(market: AgentMarketContext) -> MultiTimeframeResult:
    """M15 comes from the caller; H1/H4/D1 are loaded. Daily is real D1, not a resample of H1."""
    m15 = _trend_to_bias(run_structure_agent(market).trend)
    h1_ctx = build_agent_market_context(DATA_SYMBOL, "1h", limit=120)
    h4_ctx = build_agent_market_context(DATA_SYMBOL, "4h", limit=120)
    d1_ctx = build_agent_market_context(DATA_SYMBOL, "1d", limit=120)
    h1 = _bias_from_context(h1_ctx)
    h4 = _bias_from_context(h4_ctx)
    daily = _bias_from_context(d1_ctx)
    conflict = (
        m15 in ("bullish", "bearish")
        and h4 in ("bullish", "bearish")
        and m15 != h4
    )
    directional = [bias for bias in (m15, h1, h4, daily) if bias in ("bullish", "bearish")]
    aligned = len(directional) == 4 and len(set(directional)) == 1
    return MultiTimeframeResult(
        current_bias=m15,
        higher_bias=h4,
        daily_bias=daily,
        conflict=conflict,
        m15_bias=m15,
        h1_bias=h1,
        h4_bias=h4,
        aligned=aligned,
    )
