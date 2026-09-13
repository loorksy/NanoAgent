"""Gold trading tools — analyze and quote."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import ToolContext, current_request_context
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema
from nanobot.trading.config import load_trading_config
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError
from nanobot.trading.intent_router import resolve_team_preset
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.chart_capture import resolve_visual_capture
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import run_swarm

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus

_QUOTE_PARAMETERS = tool_parameters_schema(
    symbol=StringSchema("Trading symbol (gold only, default XAUUSD)"),
)

_ANALYZE_PARAMETERS = tool_parameters_schema(
    interval=StringSchema(
        "Candle interval for analysis (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    team_mode=StringSchema(
        "Analysis team mode (default core)",
        enum=["core", "debate", "swarm"],
    ),
    preset=StringSchema(
        "Swarm preset when team_mode=swarm "
        "(gold_analysis_committee, gold_debate_desk, gold_news_war_room, gold_mtf_panel)"
    ),
    required=[],
)


def _request_route() -> tuple[str, str]:
    ctx = current_request_context()
    if ctx is None:
        return "", ""
    return ctx.channel or "", ctx.chat_id or ""


@tool_parameters(_QUOTE_PARAMETERS)
class GetGoldQuoteTool(Tool):
    """Fetch the live XAUUSD quote from OANDA."""

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls()

    @property
    def name(self) -> str:
        return "get_gold_quote"

    @property
    def description(self) -> str:
        return (
            "Get the current live gold (XAUUSD) bid/ask/mid price from the platform "
            "OANDA feed. Use this for price questions before running a full analysis."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, symbol: str = DATA_SYMBOL, **kwargs: Any) -> str:
        config = load_trading_config()
        if not config.oanda_configured:
            return ToolResult.error("OANDA is not configured — cannot fetch gold quote.")
        try:
            quote = fetch_quote(symbol, config=config)
        except GoldOnlyError as exc:
            return ToolResult.error(str(exc))
        except Exception as exc:
            return ToolResult.error(f"Failed to fetch quote: {exc}")
        if quote is None:
            return ToolResult.error("No quote returned from OANDA.")
        return json.dumps(
            {
                "symbol": quote.symbol,
                "bid": quote.bid,
                "ask": quote.ask,
                "mid": quote.mid,
                "tradeable": quote.tradeable,
            },
            indent=2,
        )


@tool_parameters(_ANALYZE_PARAMETERS)
class AnalyzeGoldTool(Tool):
    """Run the full gold recommendation pipeline and open the side chart."""

    def __init__(self, bus: MessageBus | None, subagent_manager: Any | None) -> None:
        self._bus = bus
        self._subagent_manager = subagent_manager

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus, subagent_manager=ctx.subagent_manager)

    @property
    def name(self) -> str:
        return "analyze_gold"

    @property
    def description(self) -> str:
        return (
            "Run a full XAUUSD gold analysis through the specialist fleet and G1–G4, "
            "G6–G7 gates. Opens the TradingView chart side panel, streams stages, and "
            "returns buy/sell/wait with entry, stop, and targets. Use team_mode=debate "
            "or team_mode=swarm with preset for multi-agent teams. For price-only "
            "questions use get_gold_quote instead."
        )

    async def execute(
        self,
        interval: str = "15m",
        team_mode: str = "core",
        preset: str | None = None,
        **kwargs: Any,
    ) -> str:
        channel, chat_id = _request_route()
        publisher = TradingStagePublisher(self._bus, channel=channel, chat_id=chat_id)
        await publisher.open_chart(interval)
        visual_capture = resolve_visual_capture(publisher)

        try:
            if team_mode == "debate":
                debate = await run_debate_crew(
                    user_message=(current_request_context().original_user_text if current_request_context() else "") or "",
                    emit=publisher.sync_emit,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher,
                    interval=interval,
                    visual_capture=visual_capture,
                )
                result = debate.final
            elif team_mode == "swarm":
                preset_name = preset or resolve_team_preset(
                    (current_request_context().original_user_text if current_request_context() else "") or ""
                ) or "gold_analysis_committee"
                swarm = await run_swarm(
                    preset_name,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher,
                    interval=interval,
                    emit=publisher.sync_emit,
                    visual_capture=visual_capture,
                )
                result = swarm["final"]
            else:
                result = await run_unified_chart_agent(
                    interval=interval,
                    team_mode="core",
                    emit=publisher.sync_emit,
                    visual_capture=visual_capture,
                )
        except Exception as exc:
            return ToolResult.error(f"Gold analysis failed: {exc}")

        if result is None:
            return ToolResult.error("Analysis produced no result.")

        wire = result_to_wire(result)
        await publisher.publish_result(wire)

        return json.dumps(wire, indent=2)
