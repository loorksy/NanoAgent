"""Recommendation candles come from OANDA and the live quote from MetaAPI."""

from __future__ import annotations

from unittest.mock import MagicMock

from mokli.trading.market_context import build_agent_market_context, live_analysis_quote
from mokli.trading.oanda import OandaCandle, OandaQuote


def _candles(count: int = 22) -> list[OandaCandle]:
    return [
        OandaCandle(
            time_ms=1_700_000_000_000 + index * 900_000,
            open=1,
            high=2,
            low=1,
            close=1.5,
            volume=1,
            complete=True,
        )
        for index in range(count)
    ]


def test_analysis_reads_oanda_candles_and_metaapi_quote(monkeypatch) -> None:
    class Config:
        metaapi_configured = True
        oanda_configured = True

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (_candles(), False),
    )

    def _oanda_quote(*_args, **_kwargs):
        raise AssertionError("oanda quote")

    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", _oanda_quote)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_metaapi_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=4134.1, ask=4134.3, mid=4134.2, tradeable=True
        ),
    )

    context = build_agent_market_context("XAUUSD", "15m", limit=24)
    quote = live_analysis_quote("XAUUSD")

    assert context.sync.ok
    assert len(context.candles) == 22
    assert context.quote_bid == 4134.1
    assert context.quote_ask == 4134.3
    assert quote is not None
    assert abs((quote.mid or 0) - 4134.2) < 1e-6


def test_analysis_uses_oanda_quote_without_metaapi(monkeypatch) -> None:
    class Config:
        metaapi_configured = False
        oanda_configured = True

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (_candles(), False),
    )

    def _metaapi(*_args, **_kwargs):
        raise AssertionError("metaapi")

    monkeypatch.setattr("mokli.trading.market_context.fetch_metaapi_quote", _metaapi)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True
        ),
    )
    context = build_agent_market_context()
    assert context.sync.ok
    assert context.quote_mid == 1.5


def test_unconfigured_oanda_reports_the_candle_feed(monkeypatch) -> None:
    monkeypatch.setattr(
        "mokli.trading.market_context.load_trading_config",
        lambda: MagicMock(oanda_configured=False, spec=["oanda_configured"]),
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
