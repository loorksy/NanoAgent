"""Run gold trading swarm presets from the agent."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import ToolContext, current_request_context
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema
from nanobot.trading.intent_router import resolve_team_preset
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import list_presets, run_swarm

_TEAM_PARAMETERS = tool_parameters_schema(
    preset=StringSchema(
        "Swarm preset name",
        enum=[
            "gold_analysis_committee",
            "gold_debate_desk",
            "gold_news_war_room",
            "gold_mtf_panel",
        ],
    ),
    interval=StringSchema(
        "Candle interval for final analysis (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    required=["preset"],
)


@tool_parameters(_TEAM_PARAMETERS)
class RunTradingTeamTool(Tool):
    """Execute a YAML-defined gold trading team preset."""

    def __init__(self, bus: Any, subagent_manager: Any | None) -> None:
        self._bus = bus
        self._subagent_manager = subagent_manager

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus, subagent_manager=ctx.subagent_manager)

    @property
    def name(self) -> str:
        return "run_trading_team"

    @property
    def description(self) -> str:
        available = ", ".join(list_presets()) or "gold_analysis_committee"
        return (
            "Run a multi-agent gold trading team preset (committee, debate desk, "
            f"news war room, or MTF panel). Available presets: {available}. "
            "Each role runs as a real subagent before the core recommendation pipeline."
        ).format(available=available)

    async def execute(
        self,
        preset: str,
        interval: str = "15m",
        **kwargs: Any,
    ) -> str:
        ctx = current_request_context()
        if ctx is None:
            return ToolResult.error("run_trading_team requires an active chat session")

        channel = ctx.channel or ""
        chat_id = ctx.chat_id or ""
        publisher = TradingStagePublisher(self._bus, channel=channel, chat_id=chat_id)
        await publisher.open_chart(interval)

        preset_name = preset or resolve_team_preset(ctx.original_user_text or "") or "gold_analysis_committee"
        try:
            swarm = await run_swarm(
                preset_name,
                subagent_manager=self._subagent_manager,
                publisher=publisher,
                interval=interval,
                emit=publisher.sync_emit,
            )
        except Exception as exc:
            return ToolResult.error(f"Swarm preset failed: {exc}")

        final = swarm.get("final")
        if final is None:
            return ToolResult.error("Swarm produced no final analysis")

        wire = result_to_wire(final)
        await publisher.publish_result(wire)
        return json.dumps(
            {
                "preset": preset_name,
                "task_summaries": swarm.get("task_summaries", []),
                "final": wire,
            },
            indent=2,
        )
