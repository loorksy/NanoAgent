"""Run gold trading swarm presets from the agent."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import ToolContext, current_request_context
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema
from nanobot.agent.tools.trading_chart import AnalyzeGoldTool
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

    def __init__(self, bus: Any) -> None:
        self._bus = bus

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus)

    @property
    def name(self) -> str:
        return "run_trading_team"

    @property
    def description(self) -> str:
        available = ", ".join(list_presets()) or "gold_analysis_committee"
        return (
            "Run a multi-agent gold trading team preset (committee, debate desk, "
            f"news war room, or MTF panel). Available presets: {available}. "
            "Opens the side chart and returns the final recommendation after the "
            "swarm DAG completes."
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

        try:
            swarm = await run_swarm(preset)
        except Exception as exc:
            return ToolResult.error(f"Swarm preset failed: {exc}")

        final = swarm.get("final")
        if final is None:
            return ToolResult.error("Swarm produced no final analysis")

        from nanobot.trading.result_wire import result_to_wire
        from nanobot.trading.stage_delivery import TradingStagePublisher

        publisher = TradingStagePublisher(
            self._bus,
            channel=ctx.channel,
            chat_id=ctx.chat_id,
        )
        await publisher.open_chart(interval)
        wire = result_to_wire(final)
        await publisher.publish_result(wire)
        return json.dumps(
            {
                "preset": preset,
                "swarm_layers": swarm.get("layers", []),
                "final": wire,
            },
            indent=2,
        )
