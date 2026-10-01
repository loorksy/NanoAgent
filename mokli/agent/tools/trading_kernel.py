"""Unified-loop kernel and gate-report tools — registered only when loop is not off."""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from mokli.agent.tools.base import Tool, ToolResult, tool_parameters
from mokli.agent.tools.context import (
    ToolContext,
    current_request_session_key,
)
from mokli.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from mokli.events import DecisionCompletedEvent
from mokli.trading.kernel import run_trading_kernel
from mokli.trading.locale import active_locale
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.recommendations.gate_report import build_gate_report_result
from mokli.trading.result_wire import brief_for_model, decision_card_payload, result_to_wire
from mokli.trading.tool_delivery import should_publish_trading_ui
from mokli.trading.tool_errors import (
    cached_decision_result,
    model_json,
    remember_decision_error,
)

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
            "When true, this call runs the gold_decision_review team and then the kernel. "
            "Do not call run_trading_team first. A later call in this turn returns the "
            "result already produced, including a failed attempt, unless force_new_plan "
            "or reevaluate is set."
        ),
    ),
    present_ui=BooleanSchema(
        description="When true, stream trading cards. Default false.",
    ),
    required=[],
)

_GATE_PARAMETERS = tool_parameters_schema(required=[])


async def _prefetch_synthesis_evidence(interval: str, turn: Any) -> None:
    """Load the synthesis nodes while a team brief is still running."""
    from mokli.trading.evidence.node_sets import SYNTHESIS_REQUIRED_NODES
    from mokli.trading.unified_evidence import fetch_evidence_nodes

    await fetch_evidence_nodes(
        sorted(SYNTHESIS_REQUIRED_NODES),
        interval=interval,
        session=turn,
    )


def start_synthesis_prefetch(interval: str, turn: Any) -> asyncio.Task[None]:
    """Evidence does not read the team brief, so it can run beside the roles."""
    return asyncio.create_task(_prefetch_synthesis_evidence(interval, turn))


async def finish_synthesis_prefetch(prefetch: asyncio.Task[None] | None) -> None:
    """Wait for the overlap. A failed fetch leaves the kernel to gather what is missing."""
    if prefetch is None:
        return
    try:
        await prefetch
    except Exception:
        pass


async def publish_kernel_decision(bus: Any | None, result: Any) -> None:
    """Publish the decision card when the kernel returned a verdict.

    A missing bus, a missing session, or a result that is not a verdict
    publishes nothing. A publish failure does not replace the tool result.
    """
    card = decision_card_payload(result)
    if card is None or bus is None or not hasattr(bus, "publish"):
        return
    from mokli.agent.tools.context import current_request_context

    request = current_request_context()
    session_key = request.session_key if request is not None else None
    if not session_key:
        return
    try:
        await bus.publish(DecisionCompletedEvent(session_key=session_key, payload=card))
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("kernel decision card was not published")


async def cancel_synthesis_prefetch(prefetch: asyncio.Task[None] | None) -> None:
    if prefetch is None or prefetch.done():
        return
    prefetch.cancel()
    try:
        await prefetch
    except (asyncio.CancelledError, Exception):
        pass


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
        if (
            turn is not None
            and turn.decision_wire
            and not reevaluate
            and not force_new_plan
        ):
            return turn.decision_wire
        cached_failure = cached_decision_result(
            self.name,
            {"reevaluate": reevaluate, "force_new_plan": force_new_plan},
        )
        if cached_failure is not None:
            return cached_failure
        if decision_review:
            from mokli.agent.tools.context import current_request_session_key
            from mokli.trading.tool_errors import live_plan_block_if_any

            blocked = await live_plan_block_if_any(
                current_request_session_key(),
                reevaluate=reevaluate,
                force_new_plan=force_new_plan,
            )
            if blocked is not None:
                return blocked
        team_briefing: str | None = None
        team_mode = "core"
        swarm_agents: list[Any] = []
        swarm_drivers: list[Any] = []
        # Evidence does not read the team brief. Gather it while the roles run.
        prefetch: asyncio.Task[None] | None = None
        if decision_review and turn is not None and not turn.decision_wire:
            prefetch = start_synthesis_prefetch(interval, turn)
        try:
            if decision_review:
                from mokli.trading.teams.runtime import review_round_limit, run_swarm

                swarm = await run_swarm(
                    "gold_decision_review",
                    subagent_manager=self._subagent_manager,
                    interval=interval,
                    bus=self._bus,
                    max_review_rounds=review_round_limit(),
                )
                team_briefing = str(swarm.get("team_briefing") or "")
                team_mode = "gold_decision_review"
                agents = swarm.get("team_agents")
                drivers = swarm.get("macro_drivers")
                if isinstance(agents, list):
                    swarm_agents = agents
                if isinstance(drivers, list):
                    swarm_drivers = drivers
            await finish_synthesis_prefetch(prefetch)
            prefetch = None
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
            return remember_decision_error(ToolResult.error(str(exc.reason)))
        except Exception as exc:
            return remember_decision_error(
                ToolResult.error(f"Gold analysis failed: {exc}")
            )
        finally:
            await cancel_synthesis_prefetch(prefetch)
        if swarm_agents:
            result.team_agents = list(swarm_agents)
        if swarm_drivers:
            result.macro_drivers = list(swarm_drivers)
        await publish_kernel_decision(self._bus, result)
        payload = model_json(brief_for_model(result_to_wire(result)))
        if decision_review and turn is not None:
            turn.decision_wire = payload
            turn.decision_error = None
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
        from mokli.trading.recommendations.lifecycle import grade_session_plan

        live, _quote = await grade_session_plan(current_request_session_key())
        result = build_gate_report_result(live, operator_text="", locale=locale)
        return model_json(brief_for_model(result_to_wire(result), include_gates=True))
