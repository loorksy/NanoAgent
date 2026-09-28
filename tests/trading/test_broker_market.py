"""Broker catalog, ticks, and candles stay on the connected account."""

from __future__ import annotations

import json
import time

from mokli.agent.tools.mt5_market import Mt5ListSymbolsTool, Mt5MarketTool
from mokli.trading.broker_market import bar_count, candles_from_rates, quote_view
from mokli.trading.mt5_broker import (
    _compact_symbols,
    _filter_symbols,
    resolve_symbol_name,
    set_transport_for_tests,
)


def test_compact_catalog_does_not_pull_full_symbol_records() -> None:
    class Conn:
        def eval(self, code: str) -> list[dict]:
            assert "symbols_get" in code
            assert "trade_mode" in code
            return [
                {
                    "name": "EURUSD",
                    "description": "Euro",
                    "digits": 5,
                    "path": "Forex",
                    "trade_mode": 4,
                }
            ]

    class Client:
        _MetaTrader5__conn = Conn()

        def symbols_get(self) -> list[dict]:
            raise AssertionError("full catalog")

    rows = _compact_symbols(Client())
    assert rows[0]["name"] == "EURUSD"


def test_typed_gold_name_resolves_to_the_account_symbol() -> None:
    rows = [
        {"name": "BTCXAUm"},
        {"name": "XAUUSDm"},
        {"name": "XAUEURm"},
    ]
    assert resolve_symbol_name(rows, "XAUUSD") == "XAUUSDm"
    assert resolve_symbol_name([{"name": "XAUUSD"}, {"name": "XAUUSDm"}], "xauusd") == "XAUUSD"
    assert resolve_symbol_name(rows, "EURUSD") is None


def test_symbol_catalog_hides_disabled_names_and_matches_the_query() -> None:
    rows = [
        {"name": "EURUSD", "description": "Euro vs US Dollar", "digits": 5, "path": "Forex", "trade_mode": 4},
        {"name": "XAUUSD", "description": "Gold", "digits": 2, "path": "Metals", "trade_mode": 4},
        {"name": "OLD", "description": "retired", "digits": 2, "path": "Forex", "trade_mode": 0},
    ]
    payload = _filter_symbols(rows, query="eur", limit=10)
    assert payload["total"] == 1
    assert payload["symbols"][0]["name"] == "EURUSD"
    assert "trade_mode" in payload["symbols"][0]
    dumped = json.dumps(payload)
    assert "password" not in dumped
    assert "OLD" not in dumped


def test_quote_and_candles_use_terminal_fields() -> None:
    assert quote_view({"ok": False, "error": "down"}) is None
    view = quote_view(
        {"ok": True, "quote": {"symbol": "EURUSD", "bid": 1.1, "ask": 1.2, "time": 50}}
    )
    assert view is not None
    assert view["mid"] == 1.15
    assert view["spread"] == 0.09999999999999987 or abs(view["spread"] - 0.1) < 1e-9
    assert view["source"] == "mt5"
    candles = candles_from_rates(
        [
            {"time": 200, "open": 1, "high": 2, "low": 0.5, "close": 1.4, "tick_volume": 3},
            {"time": 100, "open": 1, "high": 1, "low": 1, "close": 1, "tick_volume": 1},
        ],
        from_ms=150_000,
    )
    assert [row["time"] for row in candles] == [200]
    assert candles[0]["complete"] is False
    assert candles[0]["volume"] == 3


def test_older_chart_window_fetches_back_to_that_window() -> None:
    now_ms = int(time.time() * 1000)
    from_ms = now_ms - 2 * 24 * 3600 * 1000
    to_ms = from_ms + 3600 * 1000
    count = bar_count("5m", 300, from_ms, to_ms)
    assert count >= 2 * 24 * 12
    assert bar_count("15m", 240, None, None) == 240


async def test_agent_reads_every_symbol_from_the_account() -> None:
    class Transport:
        async def quote(self, symbol: str) -> dict:
            return {
                "ok": True,
                "quote": {"symbol": symbol, "bid": 10.0, "ask": 11.0, "time": 3, "spread": 1.0},
            }

        async def candles(self, symbol: str, timeframe: str, count: int) -> list[dict]:
            del symbol, timeframe, count
            return [
                {"time": 3, "open": 10, "high": 12, "low": 9, "close": 11, "tick_volume": 1}
            ]

        async def list_symbols(self, query: str, limit: int) -> dict:
            del query, limit
            return {
                "ok": True,
                "total": 1,
                "symbols": [
                    {"name": "EURUSD", "description": "Euro", "digits": 5, "path": "Forex"}
                ],
            }

    set_transport_for_tests(Transport())
    try:
        listed = json.loads(await Mt5ListSymbolsTool().execute(q="eur"))
        assert listed["symbols"][0]["name"] == "EURUSD"
        market = json.loads(await Mt5MarketTool().execute(symbol="EURUSD", interval="15m"))
        assert market["source"] == "mt5"
        assert market["bid"] == 10.0
        assert market["ask"] == 11.0
        assert market["candles"][0]["close"] == 11
        assert "password" not in json.dumps(market)
    finally:
        set_transport_for_tests(None)
