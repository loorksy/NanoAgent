"""Read every tradable symbol and its live prices from the connected MT5 account."""

from __future__ import annotations

import json
from typing import Any

from mokli.agent.tools.base import Tool
from mokli.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema
from mokli.trading.broker_market import broker_candles, broker_quote, broker_symbols


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


class Mt5ListSymbolsTool(Tool):
    _scopes = {"core"}

    @property
    def name(self) -> str:
        return "mt5_list_symbols"

    @property
    def description(self) -> str:
        return (
            "List tradable symbols on the operator's connected MT5 account. "
            "Pass q to filter by name, description, or path (for example gold, EUR, US30). "
            "Use the returned name exactly in mt5_market. This is the broker catalog, "
            "not a fixed gold-only list."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            q=StringSchema("Optional filter such as EUR, XAU, or US30"),
            limit=IntegerSchema(description="How many matches to return", minimum=1, maximum=200),
            required=[],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, q: str = "", limit: int = 80, **kwargs: Any) -> Any:
        del kwargs
        payload = await broker_symbols(q or "", int(limit or 80))
        symbols = payload.get("symbols") if isinstance(payload, dict) else None
        if not payload.get("ok"):
            return _json(
                {
                    "ok": False,
                    "source": "mt5",
                    "symbols": [],
                    "instruction": "The MT5 account is not connected, so the symbol list is empty.",
                }
            )
        rows = [
            {
                "name": row.get("name"),
                "description": row.get("description"),
                "digits": row.get("digits"),
                "path": row.get("path"),
            }
            for row in symbols or []
            if isinstance(row, dict)
        ]
        return _json(
            {
                "ok": True,
                "source": "mt5",
                "total": payload.get("total", len(rows)),
                "symbols": rows,
                "instruction": (
                    "These names are the pairs on the operator's broker account. "
                    "Call mt5_market with one name for the live bid, ask, spread, and candles."
                ),
            }
        )


class Mt5MarketTool(Tool):
    _scopes = {"core"}

    @property
    def name(self) -> str:
        return "mt5_market"

    @property
    def description(self) -> str:
        return (
            "Live bid, ask, spread, and recent candles for one symbol on the operator's "
            "MT5 account. The numbers are the broker's own ticks and rates. "
            "Call mt5_list_symbols first if the exact symbol name is unknown. "
            "Quote the returned bid/ask/spread verbatim and do not say the feed is unavailable "
            "when this tool returns prices."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            symbol=StringSchema("Broker symbol name, such as EURUSD or XAUUSD"),
            interval=StringSchema(
                "Candle size",
                enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            ),
            limit=IntegerSchema(description="How many recent candles", minimum=1, maximum=500),
            required=["symbol"],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 50,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        name = str(symbol or "").strip()
        if not name:
            return _json({"ok": False, "instruction": "Pass a symbol from mt5_list_symbols."})
        quote = await broker_quote(name)
        candles = await broker_candles(name, interval or "15m", int(limit or 50))
        view = quote.get("quote") if isinstance(quote, dict) else None
        bars = candles.get("candles") if isinstance(candles, dict) else []
        if not isinstance(view, dict):
            return _json(
                {
                    "ok": False,
                    "symbol": name,
                    "source": "mt5",
                    "instruction": (
                        "The broker did not return a tick for this symbol. "
                        "Check the name with mt5_list_symbols. Do not invent a price."
                    ),
                }
            )
        recent = list(bars or [])[-12:]
        return _json(
            {
                "ok": True,
                "source": "mt5",
                "symbol": view.get("symbol") or name,
                "bid": view.get("bid"),
                "ask": view.get("ask"),
                "mid": view.get("mid"),
                "spread": view.get("spread"),
                "time": view.get("time"),
                "interval": interval or "15m",
                "candles": recent,
                "instruction": (
                    "bid, ask, and spread are the live broker tick. "
                    "candles are that account's rates, oldest first, and the last bar is still forming."
                ),
            }
        )
