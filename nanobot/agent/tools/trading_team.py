"""Run gold trading swarm presets from the agent."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema

_TEAM_PARAMETERS = tool_parameters_schema(
    preset=StringSchema("Swarm preset name (currently disabled)"),
    interval=StringSchema(
        "Candle interval for final analysis (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    required=["preset"],
)

_TEAM_UNAVAILABLE = (
    "Multi-agent trading teams are not available yet. "
    "Use analyze_gold for the core gold analysis pipeline."
)


@tool_parameters(_TEAM_PARAMETERS)
class RunTradingTeamTool(Tool):
    """Execute a YAML-defined gold trading team preset."""

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls()

    @property
    def name(self) -> str:
        return "run_trading_team"

    @property
    def description(self) -> str:
        return (
            "Reserved for future multi-agent gold teams. Currently disabled — "
            "use analyze_gold for full XAUUSD analysis."
        )

    async def execute(self, preset: str, interval: str = "15m", **kwargs: Any) -> str:
        return ToolResult.error(_TEAM_UNAVAILABLE)
