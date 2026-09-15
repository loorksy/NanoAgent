"""Gold trading tools — analyze and quote."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import (
    ToolContext,
    current_request_context,
    current_request_session_key,
)
from nanobot.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from nanobot.trading.cards.artifacts import build_price_quote_artifacts
from nanobot.trading.config import load_trading_config
from nanobot.trading.locale import locale_from_text
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.chart_capture import resolve_visual_capture
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.recommendations.followup import grade_outcome_status
from nanobot.trading.recommendations.lifecycle import (
    close_plan_for_session,
    list_session_archive,
    prepare_for_new_recommendation,
    sync_session_live_plan,
)
from nanobot.trading.recommendations.store import latest_live_recommendation
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import run_swarm
from nanobot.trading.tool_delivery import should_publish_trading_ui

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus

_QUOTE_PARAMETERS = tool_parameters_schema(
    symbol=StringSchema("Trading symbol (gold only, default XAUUSD)"),
    present_ui=BooleanSchema(
        description=(
            "When true, push a price-quote card to the WebUI/chat. "
            "Default false — reply in chat using the returned JSON."
        ),
    ),
    required=[],
)

_CAPTURE_PARAMETERS = tool_parameters_schema(
    interval=StringSchema(
        "Lead candle interval (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    required=[],
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
    reevaluate=BooleanSchema(
        description=(
            "Re-run analysis on an existing live plan (same side only). "
            "Default false — use get_live_recommendation for status/price follow-ups."
        ),
    ),
    force_new_plan=BooleanSchema(
        description=(
            "When true, auto-archive a terminal plan (invalidated/tp1/expired) for this "
            "conversation before running analysis. Use after the operator confirms a new "
            "recommendation once the prior plan is closed."
        ),
    ),
    present_ui=BooleanSchema(
        description=(
            "When true, open the chart panel and stream trading cards. "
            "Default false — return structured JSON for you to summarize in chat."
        ),
    ),
    required=[],
)

_LIVE_PLAN_PARAMETERS = tool_parameters_schema(
    present_ui=BooleanSchema(
        description=(
            "When true, push plan-status artifacts to the WebUI/chat. "
            "Default false — reply in chat using the returned JSON."
        ),
    ),
    required=[],
)

_MANAGE_PLAN_PARAMETERS = tool_parameters_schema(
    action=StringSchema(
        "Lifecycle action for this conversation's recommendation.",
        enum=["sync", "prepare_new", "close_plan", "list_archive"],
    ),
    archive_category=StringSchema(
        "Optional filter when action=list_archive",
        enum=["invalidated", "win", "loss", "modified", "superseded", "expired", "other"],
    ),
    close_status=StringSchema(
        "Status written when action=close_plan (default superseded)",
        enum=["superseded", "invalidated", "expired"],
    ),
    required=["action"],
)


def _request_route() -> tuple[str, str]:
    ctx = current_request_context()
    if ctx is None:
        return "", ""
    return ctx.channel or "", ctx.chat_id or ""


def _operator_locale() -> str:
    operator_text = (
        current_request_context().original_user_text if current_request_context() else ""
    ) or ""
    return locale_from_text(operator_text)


async def _maybe_publish_artifacts(
    bus: MessageBus | None,
    *,
    channel: str,
    chat_id: str,
    locale: str,
    artifacts: list[dict[str, Any]],
    present_ui: bool,
) -> None:
    if not should_publish_trading_ui(present_ui):
        return
    if bus is None or not channel or not chat_id or not artifacts:
        return
    publisher = TradingStagePublisher(
        bus,
        channel=channel,
        chat_id=chat_id,
        locale=locale,
    )
    await publisher.publish_artifacts(artifacts, locale=locale)


def _build_plan_status_artifact(
    row: dict[str, Any],
    *,
    locale: str,
    live_price: float | None,
    outcome_status: str,
) -> dict[str, Any]:
    from nanobot.trading.i18n import artifact_title

    return {
        "type": "plan_status",
        "title": artifact_title("plan_status", locale),
        "payload": {
            "id": str(row.get("id") or ""),
            "direction": str(row.get("direction") or "wait"),
            "status": outcome_status,
            "livePrice": live_price,
            "entry": row.get("entry"),
            "stopLoss": row.get("stop_loss"),
            "targets": list(row.get("targets") or []),
            "summary": str(row.get("summary") or ""),
        },
    }


@tool_parameters(_QUOTE_PARAMETERS)
class GetGoldQuoteTool(Tool):
    """Fetch the live XAUUSD quote from the platform market feed."""

    def __init__(self, bus: MessageBus | None) -> None:
        self._bus = bus

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus)

    @property
    def name(self) -> str:
        return "get_gold_quote"

    @property
    def description(self) -> str:
        return (
            "Get the current live gold (XAUUSD) bid/ask/mid price from the platform "
            "market feed. Use for any price question or before quoting levels in chat. "
            "Always use the returned mid/bid/ask in your reply — never invent prices. "
            "Set present_ui=true only when the operator explicitly wants a visual quote card."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        symbol: str = DATA_SYMBOL,
        present_ui: bool = False,
        **kwargs: Any,
    ) -> str:
        config = load_trading_config()
        if not config.oanda_configured:
            return ToolResult.error("Market data is not available — cannot fetch gold quote.")
        try:
            quote = fetch_quote(symbol, config=config)
        except GoldOnlyError as exc:
            return ToolResult.error(str(exc))
        except Exception as exc:
            return ToolResult.error(f"Failed to fetch quote: {exc}")
        if quote is None:
            return ToolResult.error("No live quote is available right now.")
        locale = _operator_locale()
        quote_data = {
            "symbol": quote.symbol,
            "bid": quote.bid,
            "ask": quote.ask,
            "mid": quote.mid,
            "tradeable": quote.tradeable,
        }
        artifacts = build_price_quote_artifacts(quote_data, locale=locale)
        channel, chat_id = _request_route()
        await _maybe_publish_artifacts(
            self._bus,
            channel=channel,
            chat_id=chat_id,
            locale=locale,
            artifacts=artifacts,
            present_ui=present_ui,
        )
        return json.dumps(
            {
                **quote_data,
                "locale": locale,
                "display": {
                    "bid": f"{quote.bid:.2f}" if quote.bid is not None else None,
                    "ask": f"{quote.ask:.2f}" if quote.ask is not None else None,
                    "mid": f"{quote.mid:.2f}" if quote.mid is not None else None,
                },
                "instruction": "Quote display.mid (or bid/ask) verbatim — never invent or reformat with commas.",
                "artifacts": artifacts if should_publish_trading_ui(present_ui) else [],
            },
            indent=2,
        )


@tool_parameters(_LIVE_PLAN_PARAMETERS)
class GetLiveRecommendationTool(Tool):
    """Return the active live recommendation for this conversation."""

    def __init__(self, bus: MessageBus | None) -> None:
        self._bus = bus

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus)

    @property
    def name(self) -> str:
        return "get_live_recommendation"

    @property
    def description(self) -> str:
        return (
            "Read the current live gold recommendation for this chat session, "
            "including entry/stop/targets, graded outcome status, and the live "
            "XAUUSD mid price. Use for follow-ups, plan status, and TP/SL progress — "
            "do not call analyze_gold for these. Set present_ui=true only when a "
            "visual plan-status card helps the operator."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, present_ui: bool = False, **kwargs: Any) -> str:
        locale = _operator_locale()
        session_key = current_request_session_key()
        live = sync_session_live_plan(session_key)
        if not live:
            return json.dumps(
                {
                    "has_live_plan": False,
                    "locale": locale,
                },
                indent=2,
            )

        live_price: float | None = None
        quote_data: dict[str, Any] | None = None
        config = load_trading_config()
        if config.oanda_configured:
            try:
                quote = fetch_quote(DATA_SYMBOL, config=config)
                if quote is not None:
                    live_price = quote.mid
                    quote_data = {
                        "symbol": quote.symbol,
                        "bid": quote.bid,
                        "ask": quote.ask,
                        "mid": quote.mid,
                        "tradeable": quote.tradeable,
                    }
            except Exception:
                pass

        outcome_status = grade_outcome_status(live, live_price=live_price)
        can_issue_new = outcome_status in {"invalidated", "tp1", "expired", "superseded"}

        def _plain(value: object | None) -> str | None:
            if value is None:
                return None
            try:
                return f"{float(value):.2f}"
            except (TypeError, ValueError):
                return None

        payload: dict[str, Any] = {
            "has_live_plan": True,
            "locale": locale,
            "plan": {
                "id": live.get("id"),
                "direction": live.get("direction"),
                "entry": live.get("entry"),
                "stop_loss": live.get("stop_loss"),
                "targets": list(live.get("targets") or []),
                "status": live.get("status"),
                "outcome_status": outcome_status,
                "summary": live.get("summary"),
                "confidence": live.get("confidence"),
                "interval": live.get("interval"),
            },
            "live_price": live_price,
            "quote": quote_data,
            "display": {
                "live_price": _plain(live_price),
                "entry": _plain(live.get("entry")),
                "stop_loss": _plain(live.get("stop_loss")),
                "targets": [_plain(t) for t in list(live.get("targets") or [])],
            },
            "instruction": (
                "Use display.* strings verbatim for prices in your reply. "
                "XAUUSD is near 4300+ on this feed — never write 3300-range prices. "
                + (
                    "Plan is terminal — call analyze_gold with force_new_plan=true for a fresh recommendation."
                    if can_issue_new
                    else ""
                )
            ),
        }

        artifacts: list[dict[str, Any]] = []
        if should_publish_trading_ui(present_ui):
            artifacts = [_build_plan_status_artifact(
                live,
                locale=locale,
                live_price=live_price,
                outcome_status=outcome_status,
            )]
            channel, chat_id = _request_route()
            await _maybe_publish_artifacts(
                self._bus,
                channel=channel,
                chat_id=chat_id,
                locale=locale,
                artifacts=artifacts,
                present_ui=True,
            )
        payload["artifacts"] = artifacts
        return json.dumps(payload, indent=2)


@tool_parameters(_MANAGE_PLAN_PARAMETERS)
class ManageTradingPlanTool(Tool):
    """Archive, sync, and close trading recommendations for this session."""

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls()

    @property
    def name(self) -> str:
        return "manage_trading_plan"

    @property
    def description(self) -> str:
        return (
            "Manage the conversation's gold recommendation lifecycle: sync outcomes to "
            "the database, auto-clear terminal plans, close a live plan, or list archived "
            "history (invalidated, win, loss, modified, superseded). Use before analyze_gold "
            "when the operator wants a new recommendation but a stale plan still blocks."
        )

    @property
    def read_only(self) -> bool:
        return False

    async def execute(
        self,
        action: str,
        archive_category: str | None = None,
        close_status: str = "superseded",
        **kwargs: Any,
    ) -> str:
        session_key = current_request_session_key()
        locale = _operator_locale()
        if action == "sync":
            live = sync_session_live_plan(session_key)
            payload = {"ok": True, "has_live_plan": live is not None, "live_plan": live}
        elif action == "prepare_new":
            payload = prepare_for_new_recommendation(session_key)
            payload["ok"] = True
        elif action == "close_plan":
            if not session_key:
                return ToolResult.error("No session key for this conversation.")
            from nanobot.trading.recommendations.state_machine import classify_archive_category

            bucket = classify_archive_category(close_status, close_reason="operator_close")
            payload = close_plan_for_session(
                session_key,
                status=close_status,
                reason="operator_close",
                category=bucket,
            )
        elif action == "list_archive":
            rows = list_session_archive(session_key, category=archive_category)
            payload = {"ok": True, "archive": rows, "count": len(rows)}
        else:
            return ToolResult.error(f"Unknown action: {action}")
        payload["locale"] = locale
        payload["instruction"] = (
            "After prepare_new or closing a terminal plan, call analyze_gold "
            "(force_new_plan=true if a live plan was superseded)."
        )
        return json.dumps(payload, indent=2)


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
            "Run a full XAUUSD gold analysis through the specialist fleet and quality "
            "checks. Use only when the operator wants a new or re-evaluated recommendation. "
            "For price-only questions use get_gold_quote. For live-plan follow-ups use "
            "get_live_recommendation. Set present_ui=true to open the chart panel and "
            "stream visual cards. team_mode=swarm requires an explicit preset."
        )

    async def execute(
        self,
        interval: str = "15m",
        team_mode: str = "core",
        preset: str | None = None,
        reevaluate: bool = False,
        force_new_plan: bool = False,
        present_ui: bool = False,
        **kwargs: Any,
    ) -> str:
        config = load_trading_config()
        session_key = current_request_session_key()
        prepare_for_new_recommendation(session_key)
        if config.agent_first_mode and not reevaluate:
            live = latest_live_recommendation(session_key)
            if live:
                if force_new_plan:
                    closed = close_plan_for_session(
                        session_key or "",
                        status="superseded",
                        reason="operator_force_new",
                        category="modified",
                    )
                    if not closed.get("ok"):
                        return ToolResult.error(
                            "Could not close the active plan. Use manage_trading_plan with "
                            "action=close_plan first."
                        )
                else:
                    return ToolResult.error(
                        "This conversation already has a live recommendation. "
                        "Use get_live_recommendation for price/status follow-ups, "
                        "manage_trading_plan to archive/close, or pass force_new_plan=true "
                        "when the operator confirms a new recommendation."
                    )

        channel, chat_id = _request_route()
        locale = _operator_locale()
        publisher = TradingStagePublisher(
            self._bus,
            channel=channel,
            chat_id=chat_id,
            locale=locale,
        )
        publish_ui = should_publish_trading_ui(present_ui)
        if publish_ui:
            await publisher.open_chart(interval)
        visual_capture = resolve_visual_capture(publisher) if publish_ui else None

        try:
            if team_mode == "debate":
                debate = await run_debate_crew(
                    user_message=(current_request_context().original_user_text if current_request_context() else "") or "",
                    emit=publisher.sync_emit if publish_ui else None,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher if publish_ui else None,
                    interval=interval,
                    visual_capture=visual_capture,
                )
                result = debate.final
            elif team_mode == "swarm":
                if not preset:
                    return ToolResult.error(
                        "team_mode=swarm requires an explicit preset parameter."
                    )
                swarm = await run_swarm(
                    preset,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher if publish_ui else None,
                    interval=interval,
                    emit=publisher.sync_emit if publish_ui else None,
                    visual_capture=visual_capture,
                )
                result = swarm["final"]
            else:
                result = await run_unified_chart_agent(
                    interval=interval,
                    team_mode="core",
                    emit=publisher.sync_emit if publish_ui else None,
                    visual_capture=visual_capture,
                )
        except Exception as exc:
            return ToolResult.error(f"Gold analysis failed: {exc}")

        if result is None:
            return ToolResult.error("Analysis produced no result.")

        wire = result_to_wire(result)
        if publish_ui:
            await publisher.publish_result(wire)

        return json.dumps(wire, indent=2)


@tool_parameters(_CAPTURE_PARAMETERS)
class CaptureGoldChartTool(Tool):
    """Capture a TradingView chart screenshot for XAUUSD."""

    def __init__(self, bus: MessageBus | None) -> None:
        self._bus = bus

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(bus=ctx.bus)

    @property
    def name(self) -> str:
        return "capture_gold_chart"

    @property
    def description(self) -> str:
        return (
            "Capture a live XAUUSD chart screenshot from the WebUI TradingView side panel. "
            "Use when the operator asks for a chart image or screenshot without a full "
            "recommendation. Requires the WebUI chart panel to be open in the same session. "
            "Delivers the image to Telegram/WhatsApp when applicable."
        )

    async def execute(self, interval: str = "15m", **kwargs: Any) -> str:
        from nanobot.trading.capture_service import chart_capture_tool_result, run_chart_capture

        channel, chat_id = _request_route()
        operator_text = (
            current_request_context().original_user_text if current_request_context() else ""
        ) or ""
        payload = await run_chart_capture(
            bus=self._bus,
            channel=channel,
            chat_id=chat_id,
            interval=interval,
            operator_text=operator_text,
        )
        if not payload.get("ok"):
            message = str(payload.get("message") or "Chart capture failed.")
            hint = str(payload.get("hint") or "").strip()
            if hint:
                message = f"{message} {hint}"
            return ToolResult.error(message)
        return chart_capture_tool_result(payload)
