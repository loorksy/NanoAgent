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

    def fake(
        _symbol: str,
        interval: str,
        limit: int = 240,
        *,
        include_quote: bool = True,
    ) -> AgentMarketContext:
        nonlocal started
        assert limit == 120
        assert include_quote is False
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


def test_higher_timeframes_do_not_fetch_the_live_quote(monkeypatch) -> None:
    """Three intervals need three candle windows. The bias does not use a quote."""
    from mokli.trading.market_context import resolve_live_quote
    from mokli.trading.oanda import OandaCandle, OandaQuote
    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    quotes = {"n": 0}
    candles = {"n": 0}

    def fake_candles(*_args, **_kwargs):
        candles["n"] += 1
        row = OandaCandle(
            time_ms=1_700_000_000_000,
            open=1,
            high=2,
            low=1,
            close=1.5,
            volume=1,
            complete=True,
        )
        return [row] * 22, False

    def fake_quote(*_args, **_kwargs):
        quotes["n"] += 1
        return OandaQuote(symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True)

    class _Structure:
        trend = "uptrend"

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", fake_candles)
    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", fake_quote)
    monkeypatch.setattr(
        "mokli.trading.agents.multi_timeframe.run_structure_agent",
        lambda _market: _Structure(),
    )

    with turn_session_scope() as turn:
        result = run_multi_timeframe_agent(_market("15m"))
        assert quotes["n"] == 0
        assert turn.quote_reuses == 0
        assert candles["n"] == 3
        assert result.m15_bias == "bullish"

        resolve_live_quote("XAUUSD")
        assert quotes["n"] == 1
        assert turn.quote_reuses == 0
