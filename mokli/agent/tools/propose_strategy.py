"""Read-only strategy proposal backed by the candle replay (R14)."""

from __future__ import annotations

import asyncio
from typing import Any

from mokli.agent.tools.base import Tool
from mokli.agent.tools.fast_backtest import candles_from_json
from mokli.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from mokli.trading.strategy_lab import (
    load_replay_candles,
    model_strategy_brief,
    propose_strategy,
    request_live,
    save_strategy,
    start_paper,
)
from mokli.trading.strategy_spec import check_logic, spec_from_description
from mokli.trading.tool_errors import model_json


class ProposeStrategyTool(Tool):
    @property
    def name(self) -> str:
        return "propose_strategy"

    @property
    def description(self) -> str:
        return (
            "Design a gold strategy from a natural-language description, replay it, "
            "and optionally save or paper-trade the saved spec. "
            "A proposal is not an order. Live activation never sends a broker order."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        # ``description`` is a tool argument. Passing it as a keyword to
        # tool_parameters_schema sets the schema blurb and drops the argument.
        schema = tool_parameters_schema(
            name=StringSchema("Strategy name"),
            candles_json=StringSchema(
                "Optional OHLC JSON. Leave empty: the tool loads XAUUSD bars for the replay. "
                "Do not paste a candle list."
            ),
            action=StringSchema(
                "propose, save, paper, or activate",
                enum=["propose", "save", "paper", "activate"],
            ),
            strategy_id=StringSchema("Saved strategy id for paper or activate"),
            approve_live=BooleanSchema(
                description="Operator approval flag. Still does not place a broker order.",
            ),
            required=["name"],
        )
        schema["properties"]["description"] = StringSchema(
            "Natural-language rules. Example: gold break of the previous hour high, "
            "4h trend confirm, stop behind the last swing low, 1% risk.",
        ).to_json_schema()
        return schema

    @property
    def read_only(self) -> bool:
        return False

    async def execute(
        self,
        name: str = "",
        candles_json: str = "",
        description: str = "",
        action: str = "propose",
        strategy_id: str = "",
        approve_live: bool = False,
        **kwargs: Any,
    ) -> str:
        del kwargs
        chosen = action.strip() or "propose"
        if chosen == "paper":
            return model_json(start_paper(strategy_id.strip()))
        if chosen == "activate":
            return model_json(request_live(strategy_id.strip(), approved=bool(approve_live)))
        chosen_name = name.strip() or "atr_breakout"
        candles = candles_from_json(candles_json)
        needs_bars = chosen in {"propose", "save"}
        if description.strip() and check_logic(spec_from_description(description, name=chosen_name)):
            needs_bars = False
        confirm = None
        if needs_bars and not candles:
            candles, confirm = await asyncio.to_thread(load_replay_candles)
            if not candles or not confirm:
                return model_json(
                    {
                        "ok": False,
                        "status": "invalid",
                        "reason_key": "trading.market_feed_unconfigured",
                        "executed": False,
                        "broker_order": False,
                        "instruction": "Market candles are not configured. Do not invent prices.",
                    }
                )
        proposal = propose_strategy(
            chosen_name,
            candles,
            description=description,
            confirm_candles=confirm,
        )
        if chosen == "save":
            proposal = dict(proposal)
            proposal["saved"] = save_strategy(proposal)
        return model_json(model_strategy_brief(proposal))
