"""Higher-timeframe candle loads are independent."""

from __future__ import annotations

import threading

from mokli.trading.agents.multi_timeframe import run_multi_timeframe_agent
from mokli.trading.types import AgentMarketContext, Candle, MarketSync


def _market(interval: str) -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval=interval,
        candles=[Candle(time_ms=1, open=1, high=2, low=0.5, close=1.5)],
        last_close=1.5,
        atr=0.2,
        sync=MarketSync(ok=True),
    )


def test_higher_timeframe_fetches_overlap(monkeypatch) -> None:
    started = 0
    lock = threading.Lock()
    release = threading.Event()

    def fake(_symbol: str, interval: str, limit: int = 240) -> AgentMarketContext:
        nonlocal started
        assert limit == 120
        with lock:
            started += 1
            if started >= 3:
                release.set()
        assert release.wait(1)
        return _market(interval)

    class _Structure:
        trend = "uptrend"

    monkeypatch.setattr(
        "mokli.trading.agents.multi_timeframe.build_agent_market_context",
        fake,
    )
    monkeypatch.setattr(
        "mokli.trading.agents.multi_timeframe.run_structure_agent",
        lambda _market: _Structure(),
    )
    result = run_multi_timeframe_agent(_market("15m"))
    assert started == 3
    assert result.m15_bias == "bullish"
    assert result.h4_bias in {"bullish", "bearish", "neutral", "unknown"}
