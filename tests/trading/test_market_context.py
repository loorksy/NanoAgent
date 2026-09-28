"""Recommendation candles follow the linked account."""

from __future__ import annotations

from unittest.mock import MagicMock

from mokli.trading.market_context import build_agent_market_context, live_analysis_quote
from mokli.trading.mt5_broker import set_transport_for_tests
from mokli.trading.oanda import OandaCandle, OandaQuote


def test_analysis_reads_account_candles_when_mt5_is_linked(monkeypatch) -> None:
    class Config:
        mt5_configured = True
        oanda_configured = False

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())

    def _blocked(*_args, **_kwargs):
        raise AssertionError("external feed")

    monkeypatch.setattr("mokli.trading.oanda.fetch_candles", _blocked)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _blocked)

    base = 1_700_000_000

    class Transport:
        async def quote(self, symbol: str) -> dict:
            return {
                "ok": True,
                "quote": {"symbol": "XAUUSDm", "bid": 4134.1, "ask": 4134.3, "time": base},
            }

        async def candles(self, symbol: str, timeframe: str, count: int) -> list[dict]:
            assert symbol == "XAUUSD"
            assert timeframe == "M15"
            assert count >= 24
            return [
                {
                    "time": base + index * 900,
                    "open": 4100 + index,
                    "high": 4102 + index,
                    "low": 4098 + index,
                    "close": 4101 + index,
                    "tick_volume": 4,
                }
                for index in range(24)
            ]

        async def list_symbols(self, query: str, limit: int) -> dict:
            del query, limit
            return {"ok": True, "symbols": [{"name": "XAUUSDm"}]}

    set_transport_for_tests(Transport())
    try:
        context = build_agent_market_context("XAUUSD", "15m", limit=24)
        quote = live_analysis_quote("XAUUSD")
    finally:
        set_transport_for_tests(None)

    assert context.sync.ok
    assert len(context.candles) == 24
    assert context.quote_bid == 4134.1
    assert context.quote_ask == 4134.3
    assert context.candles[0].time_ms == base * 1000
    assert quote is not None
    assert quote.symbol == "XAUUSDm"
    assert quote.mid is not None
    assert abs(quote.mid - 4134.2) < 1e-6


def test_analysis_keeps_the_external_feed_when_no_account(monkeypatch) -> None:
    class Config:
        mt5_configured = False
        oanda_configured = True

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    rows = [
        OandaCandle(
            time_ms=1_700_000_000_000 + index * 900_000,
            open=1,
            high=2,
            low=1,
            close=1.5,
            volume=1,
            complete=True,
        )
        for index in range(22)
    ]
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (rows, False),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True
        ),
    )
    context = build_agent_market_context()
    assert context.sync.ok
    assert len(context.candles) == 22
    assert context.quote_mid == 1.5


def test_unlinked_account_still_reports_the_external_feed(monkeypatch) -> None:
    monkeypatch.setattr(
        "mokli.trading.market_context.load_trading_config",
        lambda: MagicMock(oanda_configured=False),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: ([], False),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: None,
    )
    context = build_agent_market_context()
    assert context.sync.ok is False
    assert context.sync.reason == "OANDA not configured"
