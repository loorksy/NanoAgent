"""Multi-timeframe bias agent."""

from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor

from mokli.trading.agents.structure import run_structure_agent
from mokli.trading.geometry.detectors import find_swings, infer_trend
from mokli.trading.gold import DATA_SYMBOL
from mokli.trading.market_context import build_agent_market_context
from mokli.trading.types import AgentMarketContext, Bias, MultiTimeframeResult


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


# Same window a trend role loads, so a graph prefetch and that role share one download.
HIGHER_TF_INTERVALS = ("1h", "4h", "1d")
HIGHER_TF_LIMIT = 120


def load_higher_timeframe(interval: str) -> AgentMarketContext:
    """Bars only. The bias does not use a live quote."""
    return build_agent_market_context(
        DATA_SYMBOL,
        interval,
        HIGHER_TF_LIMIT,
        include_quote=False,
    )


def run_multi_timeframe_agent(market: AgentMarketContext) -> MultiTimeframeResult:
    """M15 comes from the caller; H1/H4/D1 are loaded. Daily is real D1, not a resample of H1."""
    m15 = _trend_to_bias(run_structure_agent(market).trend)
    # Each worker gets its own context copy so the candle cache is visible.
    # The bias uses bars only, so these loads do not download a live quote.
    intervals = HIGHER_TF_INTERVALS
    contexts = [contextvars.copy_context() for _ in intervals]

    def _load(item: tuple[contextvars.Context, str]) -> AgentMarketContext:
        ctx, interval = item
        return ctx.run(load_higher_timeframe, interval)

    with ThreadPoolExecutor(max_workers=len(intervals)) as pool:
        h1_ctx, h4_ctx, d1_ctx = tuple(pool.map(_load, zip(contexts, intervals, strict=True)))
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
