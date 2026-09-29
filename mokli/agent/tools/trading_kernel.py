"""Unified-loop kernel and gate-report tools — registered only when loop is not off."""

from __future__ import annotations

import json
from typing import Any

from mokli.agent.tools.base import Tool, ToolResult, tool_parameters
from mokli.agent.tools.context import (
    ToolContext,
    current_request_session_key,
)
from mokli.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from mokli.trading.kernel import run_trading_kernel
from mokli.trading.locale import active_locale
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.recommendations.gate_report import build_gate_report_result
from mokli.trading.recommendations.lifecycle import sync_session_live_plan
from mokli.trading.result_wire import brief_for_model, result_to_wire
from mokli.trading.tool_delivery import should_publish_trading_ui

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
    decision_review=BooleanSchema(
        description=(
            "For a buy/sell question, run the gold_decision_review team first "
            "and pass its brief into the kernel. The kernel remains the only BUY/SELL path."
        ),
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
        decision_review: bool = False,
        **kwargs: Any,
    ) -> str:
        from mokli.trading.turn_session import current_turn_session

        turn = current_turn_session()
        if decision_review and turn is not None and turn.decision_wire:
            return turn.decision_wire
        team_briefing: str | None = None
        team_mode = "core"
        swarm_agents: list[Any] = []
        swarm_drivers: list[Any] = []
        try:
            if decision_review:
                from mokli.trading.teams.runtime import run_swarm

                swarm = await run_swarm(
                    "gold_decision_review",
                    subagent_manager=self._subagent_manager,
                    interval=interval,
                    bus=self._bus,
                )
                team_briefing = str(swarm.get("team_briefing") or "")
                team_mode = "gold_decision_review"
                agents = swarm.get("team_agents")
                drivers = swarm.get("macro_drivers")
                if isinstance(agents, list):
                    swarm_agents = agents
                if isinstance(drivers, list):
                    swarm_drivers = drivers
            result = await run_trading_kernel(
                interval=interval,
                gather_missing=gather_missing,
                reevaluate=reevaluate,
                force_new_plan=force_new_plan,
                present_ui=should_publish_trading_ui(present_ui),
                team_briefing=team_briefing,
                team_mode=team_mode,
            )
        except PolicyViolation as exc:
            return ToolResult.error(str(exc.reason))
        except Exception as exc:
            return ToolResult.error(f"Gold analysis failed: {exc}")
        if swarm_agents:
            result.team_agents = list(swarm_agents)
        if swarm_drivers:
            result.macro_drivers = list(swarm_drivers)
        payload = json.dumps(brief_for_model(result_to_wire(result)), indent=2)
        if decision_review and turn is not None:
            turn.decision_wire = payload
        return payload


@tool_parameters(_GATE_PARAMETERS)
class GetGateReportTool(Tool):
    """Stored gate report for the live recommendation — never runs the synthesizer."""

    _scopes = {"core"}

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
        locale = active_locale()
        live = sync_session_live_plan(current_request_session_key())
        result = build_gate_report_result(live, operator_text="", locale=locale)
        return json.dumps(brief_for_model(result_to_wire(result), include_gates=True), indent=2)
