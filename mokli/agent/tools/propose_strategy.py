"""Read-only strategy proposal backed by the candle replay (R14)."""

from __future__ import annotations

import json
from typing import Any

from mokli.agent.tools.base import Tool
from mokli.agent.tools.fast_backtest import candles_from_json
from mokli.agent.tools.schema import StringSchema, tool_parameters_schema
from mokli.trading.strategy_lab import propose_strategy


class ProposeStrategyTool(Tool):
    @property
    def name(self) -> str:
        return "propose_strategy"

    @property
    def description(self) -> str:
        return (
            "Propose a named gold strategy from a candle replay. "
            "Read-only: the result is a proposal, not an order."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            name=StringSchema("Strategy name"),
            candles_json=StringSchema("JSON list of OHLC objects"),
            required=["name", "candles_json"],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, name: str = "", candles_json: str = "", **kwargs: Any) -> str:
        del kwargs
        proposal = propose_strategy(name.strip() or "atr_breakout", candles_from_json(candles_json))
        return json.dumps(proposal, ensure_ascii=False)
