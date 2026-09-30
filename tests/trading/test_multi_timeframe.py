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


def test_higher_timeframes_share_one_live_quote(monkeypatch) -> None:
    """Three intervals need three candle windows and one in-flight quote."""
    import contextvars
    import time

    from mokli.trading.market_context import resolve_live_quote
    from mokli.trading.oanda import OandaCandle, OandaQuote
    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    quotes = {"n": 0}
    candles = {"n": 0}
    release = threading.Event()

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
        assert release.wait(timeout=1)
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

    holder: dict[str, object] = {}

    with turn_session_scope() as turn:
        ctx = contextvars.copy_context()

        def _run() -> None:
            holder["result"] = ctx.run(run_multi_timeframe_agent, _market("15m"))

        thread = threading.Thread(target=_run)
        thread.start()
        deadline = time.time() + 1
        while quotes["n"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        assert quotes["n"] == 1
        release.set()
        thread.join(timeout=1)
        assert not thread.is_alive()
        assert turn.quote_reuses == 2
        assert candles["n"] == 3
        assert holder["result"].m15_bias == "bullish"

        resolve_live_quote("XAUUSD")
        assert quotes["n"] == 2
        assert turn.quote_reuses == 2
