"""Short gold replay over warehouse or caller-supplied candles."""

from __future__ import annotations

import json
from typing import Any, cast

from mokli.agent.tools.base import Tool
from mokli.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema
from mokli.trading.backtest.engine import replay
from mokli.trading.types import Candle
from mokli.trading.warehouse import CandleWarehouse


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


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
            "(partial at 1R, stop to entry). Read-only. Pass candles_json or rely on the local warehouse."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            candles_json=StringSchema("Optional JSON list of OHLC objects", nullable=True),
            interval=StringSchema("Warehouse interval when candles_json is empty", enum=("15m", "1h", "1d")),
            limit=IntegerSchema(description="Bars to load from the warehouse", minimum=30, maximum=200),
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
        candles = candles_from_json(candles_json or "")
        if not candles:
            from pathlib import Path

            path = Path.home() / ".mokli" / "warehouse.sqlite"
            if path.is_file():
                store = CandleWarehouse(path)
                try:
                    candles = store.load("XAUUSD", interval, limit=limit)
                finally:
                    store.close()
        return _json(replay(candles))
