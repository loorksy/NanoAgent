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


def run_multi_timeframe_agent(market: AgentMarketContext) -> MultiTimeframeResult:
    current = _trend_to_bias(run_structure_agent(market).trend)
    h1 = build_agent_market_context(DATA_SYMBOL, "1h", limit=120)
    h4 = build_agent_market_context(DATA_SYMBOL, "4h", limit=120)
    higher_bias = _trend_to_bias(infer_trend(find_swings(h4.candles)))
    daily_bias = _trend_to_bias(infer_trend(find_swings(h1.candles)))
    conflict = (
        current in ("bullish", "bearish")
        and higher_bias in ("bullish", "bearish")
        and current != higher_bias
    )
    return MultiTimeframeResult(
        current_bias=current,
        higher_bias=higher_bias,
        daily_bias=daily_bias,
        conflict=conflict,
    )
