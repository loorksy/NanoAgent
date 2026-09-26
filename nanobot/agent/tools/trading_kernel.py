"""Unified-loop kernel and gate-report tools — registered only when loop is not off."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import (
    ToolContext,
    current_request_context,
    current_request_session_key,
)
from nanobot.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from nanobot.trading.config import unified_loop_serving
from nanobot.trading.kernel import run_trading_kernel
from nanobot.trading.locale import locale_from_text
from nanobot.trading.policy_guard import PolicyViolation
from nanobot.trading.recommendations.gate_report import build_gate_report_result
from nanobot.trading.recommendations.lifecycle import sync_session_live_plan
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.tool_delivery import should_publish_trading_ui

_KERNEL_PARAMETERS = tool_parameters_schema(
    interval=StringSchema(
        "Candle interval (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    gather_missing=BooleanSchema(
        description=(
            "When true, fetch SYNTHESIS_REQUIRED_NODES before the synthesizer. "
            "Default true for one-round-trip recommendation turns."
        ),
    ),
    reevaluate=BooleanSchema(
        description="Re-run analysis on an existing live plan (same side only).",
    ),
    force_new_plan=BooleanSchema(
        description="Archive the live plan and issue a new recommendation.",
    ),
    present_ui=BooleanSchema(
        description="When true, stream trading cards. Default false.",
    ),
    required=[],
)

_GATE_PARAMETERS = tool_parameters_schema(required=[])


@tool_parameters(_KERNEL_PARAMETERS)
class RunTradingKernelTool(Tool):
    """Sole BUY/SELL path: synthesizer + G1–G20 gates + store."""

    _scopes = {"core"}

    def __init__(self, bus: Any | None, subagent_manager: Any | None) -> None:
        self._bus = bus
        self._subagent_manager = subagent_manager

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool:
        return unified_loop_serving()

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus, subagent_manager=ctx.subagent_manager)

    @property
    def name(self) -> str:
        return "run_trading_kernel"

    @property
    def description(self) -> str:
        return (
            "Issue a gold recommendation: run the synthesizer and G1–G20 quality checks. "
            "This is the only tool allowed to emit BUY/SELL. "
            "For price questions use fetch_evidence(['market_data']) or get_gold_quote. "
            "Pass gather_missing=true (default) to fetch required evidence in one call. "
            "Teams and evidence tools never choose the side."
        )

    async def execute(
        self,
        interval: str = "15m",
        gather_missing: bool = True,
        reevaluate: bool = False,
        force_new_plan: bool = False,
        present_ui: bool = False,
        **kwargs: Any,
    ) -> str:
        try:
            result = await run_trading_kernel(
                interval=interval,
                gather_missing=gather_missing,
                reevaluate=reevaluate,
                force_new_plan=force_new_plan,
                present_ui=should_publish_trading_ui(present_ui),
            )
        except PolicyViolation as exc:
            return ToolResult.error(str(exc.reason))
        except Exception as exc:
            return ToolResult.error(f"Gold analysis failed: {exc}")
        return json.dumps(result_to_wire(result), indent=2)


@tool_parameters(_GATE_PARAMETERS)
class GetGateReportTool(Tool):
    """Stored gate report for the live recommendation — never runs the synthesizer."""

    _scopes = {"core"}

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool:
        return unified_loop_serving()

    @property
    def name(self) -> str:
        return "get_gate_report"

    @property
    def description(self) -> str:
        return (
            "Explain why the live gold recommendation was blocked or allowed. "
            "Does not run analysis and never emits a new BUY/SELL."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        locale = locale_from_text(
            (current_request_context().original_user_text if current_request_context() else "") or ""
        )
        live = sync_session_live_plan(current_request_session_key())
        result = build_gate_report_result(live, operator_text="", locale=locale)
        return json.dumps(result_to_wire(result), indent=2)
