"""Run gold trading swarm presets from the agent."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import ToolContext, current_request_context
from nanobot.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import list_presets, run_swarm
from nanobot.trading.tool_delivery import should_publish_trading_ui

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
    present_ui=BooleanSchema(
        description=(
            "When true, open the chart panel and stream team cards. "
            "Default false — return structured JSON for you to summarize in chat."
        ),
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
            "Each role runs as a real subagent before the core recommendation pipeline. "
            "Set present_ui=true only when the operator wants the visual team/chart experience."
        ).format(available=available)

    async def execute(
        self,
        preset: str,
        interval: str = "15m",
        present_ui: bool = False,
        **kwargs: Any,
    ) -> str:
        ctx = current_request_context()
        if ctx is None:
            return ToolResult.error("run_trading_team requires an active chat session")

        from nanobot.trading.locale import locale_from_text

        channel = ctx.channel or ""
        chat_id = ctx.chat_id or ""
        locale = locale_from_text(ctx.original_user_text or "")
        publish_ui = should_publish_trading_ui(present_ui)
        publisher = TradingStagePublisher(
            self._bus,
            channel=channel,
            chat_id=chat_id,
            locale=locale,
        )
        if publish_ui:
            await publisher.open_chart(interval)

        preset_name = (preset or "").strip()
        if not preset_name:
            return ToolResult.error("preset is required.")

        try:
            swarm = await run_swarm(
                preset_name,
                subagent_manager=self._subagent_manager,
                publisher=publisher if publish_ui else None,
                interval=interval,
                emit=publisher.sync_emit if publish_ui else None,
            )
        except Exception as exc:
            return ToolResult.error(f"Swarm preset failed: {exc}")

        final = swarm.get("final")
        if final is None:
            return ToolResult.error("Swarm produced no final analysis")

        wire = result_to_wire(final)
        if publish_ui:
            await publisher.publish_result(wire)
        return json.dumps(
            {
                "preset": preset_name,
                "task_summaries": swarm.get("task_summaries", []),
                "final": wire,
            },
            indent=2,
        )
