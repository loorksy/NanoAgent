"""MT5 MetaAPI tools — account, propose, confirm, modify, close. HITL is mandatory."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.schema import (
    BooleanSchema,
    NumberSchema,
    StringSchema,
    tool_parameters_schema,
)
from nanobot.trading.mt5_execution import (
    mt5_close_position,
    mt5_confirm_order,
    mt5_get_account,
    mt5_modify_order,
    mt5_propose_order,
)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


class Mt5GetAccountTool(Tool):
    @property
    def name(self) -> str:
        return "mt5_get_account"

    @property
    def description(self) -> str:
        return "Read MT5 account balance, quote, and open gold positions via MetaAPI (read-only)."

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(required=[])

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> Any:
        del kwargs
        return _json(await mt5_get_account())


class Mt5ProposeOrderTool(Tool):
    @property
    def name(self) -> str:
        return "mt5_propose_order"

    @property
    def description(self) -> str:
        return (
            "Create an MT5 order PROPOSAL only. Does not send to the broker. "
            "Show symbol, side, lot, entry, stop, and targets, then wait for operator confirm."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            side=StringSchema("buy or sell", enum=["buy", "sell"]),
            entry=NumberSchema(description="Proposed entry price"),
            stop=NumberSchema(description="Stop loss price"),
            targets=StringSchema("Comma-separated target prices"),
            lot=NumberSchema(description="Optional lot; if omitted, sized from 1% of balance"),
            comment=StringSchema("Broker comment / setup code"),
            order_type=StringSchema("market, limit, or stop", enum=["market", "limit", "stop"]),
            style=StringSchema("scalp or swing (magic number)", enum=["scalp", "swing"]),
            required=["side", "entry", "stop", "targets"],
        )

    async def execute(
        self,
        side: str,
        entry: float,
        stop: float,
        targets: str,
        lot: float | None = None,
        comment: str = "",
        order_type: str = "market",
        style: str = "swing",
        **kwargs: Any,
    ) -> Any:
        del kwargs
        tps = [float(x.strip()) for x in str(targets).split(",") if x.strip()]
        return _json(
            await mt5_propose_order(
                side=side,
                lot=lot,
                entry=float(entry),
                stop=float(stop),
                targets=tps,
                comment=comment,
                order_type=order_type,
                style=style,
            )
        )


class Mt5ConfirmOrderTool(Tool):
    @property
    def name(self) -> str:
        return "mt5_confirm_order"

    @property
    def description(self) -> str:
        return (
            "Send a previously proposed MT5 order. Requires confirm=true from the operator "
            "for THIS proposal id. Expired or gated proposals are refused."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            proposal_id=StringSchema("Id returned by mt5_propose_order"),
            confirm=BooleanSchema(
                description="Must be true — operator explicit approval of this order"
            ),
            required=["proposal_id", "confirm"],
        )

    async def execute(self, proposal_id: str, confirm: bool = False, **kwargs: Any) -> Any:
        del kwargs
        return _json(await mt5_confirm_order(proposal_id=proposal_id, confirm=bool(confirm)))


class Mt5ModifyOrderTool(Tool):
    @property
    def name(self) -> str:
        return "mt5_modify_order"

    @property
    def description(self) -> str:
        return "Modify an open MT5 position stop/target. Requires confirm=true for this position."

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            position_id=StringSchema("Broker position ticket"),
            stop=NumberSchema(description="New stop loss"),
            take_profit=NumberSchema(description="New take profit"),
            confirm=BooleanSchema(description="Must be true"),
            required=["position_id", "confirm"],
        )

    async def execute(
        self,
        position_id: str,
        confirm: bool = False,
        stop: float | None = None,
        take_profit: float | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        return _json(
            await mt5_modify_order(
                position_id=position_id,
                stop=stop,
                take_profit=take_profit,
                confirm=bool(confirm),
            )
        )


class Mt5ClosePositionTool(Tool):
    @property
    def name(self) -> str:
        return "mt5_close_position"

    @property
    def description(self) -> str:
        return "Close an open MT5 gold position. Requires confirm=true for this ticket."

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            position_id=StringSchema("Broker position ticket"),
            confirm=BooleanSchema(description="Must be true"),
            required=["position_id", "confirm"],
        )

    async def execute(self, position_id: str, confirm: bool = False, **kwargs: Any) -> Any:
        del kwargs
        return _json(await mt5_close_position(position_id=position_id, confirm=bool(confirm)))
