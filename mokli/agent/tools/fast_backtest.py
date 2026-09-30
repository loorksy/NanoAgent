"""Short gold replay. Empty input loads bars on the market path."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

from mokli.agent.tools.base import Tool
from mokli.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema
from mokli.trading.backtest.engine import replay
from mokli.trading.tool_errors import model_json
from mokli.trading.types import Candle
from mokli.trading.warehouse import CandleWarehouse


def _json(payload: Any) -> str:
    return model_json(payload)


def _load_market_bars(interval: str, limit: int) -> list[Candle]:
    """Bars for the ATR replay. The scorecard does not use a live quote."""
    from mokli.trading.market_context import build_agent_market_context

    market = build_agent_market_context("XAUUSD", interval, limit, include_quote=False)
    if not market.sync.ok:
        return []
    return list(market.candles)


def _load_warehouse(interval: str, limit: int) -> list[Candle]:
    path = Path.home() / ".mokli" / "warehouse.sqlite"
    if not path.is_file():
        return []
    store = CandleWarehouse(path)
    try:
        return store.load("XAUUSD", interval, limit=limit)
    finally:
        store.close()


def _model_card(card: dict[str, Any]) -> dict[str, Any]:
    """Scorecard the model reads. The R series repeats avg_r and stays out."""
    return {key: value for key, value in card.items() if key != "rs"}


def candles_from_json(raw: str) -> list[Candle]:
    if not raw.strip():
        return []
    parsed: object = json.loads(raw)
    if not isinstance(parsed, list):
        return []
    candles: list[Candle] = []
    for index, item in enumerate(cast(list[object], parsed)):
        if not isinstance(item, dict):
            continue
        row = cast(dict[str, object], item)

        def _num(key: str) -> float:
            value = row.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(key)
            return float(value)

        volume = row.get("volume")
        candles.append(
            Candle(
                time_ms=int(_num("time_ms")) if "time_ms" in row else index,
                open=_num("open"),
                high=_num("high"),
                low=_num("low"),
                close=_num("close"),
                volume=None if volume is None else _num("volume"),
            )
        )
    return candles


class FastBacktestTool(Tool):
    @property
    def name(self) -> str:
        return "fast_backtest"

    @property
    def description(self) -> str:
        return (
            "Replay the last 100-200 gold candles with an ATR breakout "
            "(partial at 1R, stop to entry). Read-only. Leave candles_json empty: "
            "the tool loads XAUUSD bars. Do not paste a candle list."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            candles_json=StringSchema(
                "Optional OHLC JSON. Leave empty: the tool loads XAUUSD bars. Do not paste a candle list.",
                nullable=True,
            ),
            interval=StringSchema("Bar interval when candles_json is empty", enum=("15m", "1h", "1d")),
            limit=IntegerSchema(description="Bars to load when candles_json is empty", minimum=30, maximum=200),
            required=[],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        candles_json: str | None = None,
        interval: str = "15m",
        limit: int = 200,
        **kwargs: Any,
    ) -> str:
        del kwargs
        chosen_interval = interval or "15m"
        chosen_limit = min(max(int(limit or 200), 30), 200)
        candles = candles_from_json(candles_json or "")
        if not candles:
            candles = await asyncio.to_thread(_load_market_bars, chosen_interval, chosen_limit)
        if not candles:
            candles = _load_warehouse(chosen_interval, chosen_limit)
        if not candles:
            return _json(
                {
                    "ok": False,
                    "reason_key": "trading.market_feed_unconfigured",
                    "trades": 0,
                    "instruction": "Market candles are not configured. Do not invent prices.",
                }
            )
        return _json(_model_card(replay(candles)))
