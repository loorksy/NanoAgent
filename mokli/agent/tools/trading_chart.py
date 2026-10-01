"""Gold trading tools — analyze and quote."""

# pyright: reportIncompatibleMethodOverride=false

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mokli.agent.tools.base import Tool, ToolResult, tool_parameters
from mokli.agent.tools.context import (
    ToolContext,
    current_request_context,
    current_request_session_key,
)
from mokli.agent.tools.schema import BooleanSchema, StringSchema, tool_parameters_schema
from mokli.trading.cards.artifacts import build_price_quote_artifacts
from mokli.trading.chart_capture import resolve_visual_capture
from mokli.trading.config import load_trading_config
from mokli.trading.crew.debate import run_debate_crew
from mokli.trading.gold import DATA_SYMBOL, GoldOnlyError, require_gold
from mokli.trading.kernel import LivePlanActive, run_trading_kernel
from mokli.trading.locale import active_locale
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.recommendations.followup import grade_outcome_status
from mokli.trading.recommendations.lifecycle import (
    close_plan_for_session,
    list_session_archive,
    prepare_for_new_recommendation,
)
from mokli.trading.result_wire import brief_for_model, result_to_wire
from mokli.trading.stage_delivery import TradingStagePublisher
from mokli.trading.teams.runtime import review_round_limit, run_swarm
from mokli.trading.tool_delivery import should_publish_trading_ui
from mokli.trading.tool_errors import (
    REASON_ANALYSIS_FAILED,
    REASON_MARKET_FEED_UNCONFIGURED,
    REASON_NO_QUOTE,
    REASON_NO_RESULT,
    REASON_NO_SESSION,
    REASON_POLICY_VIOLATION,
    REASON_PRESET_REQUIRED,
    REASON_UNKNOWN_ACTION,
    cached_decision_result,
    live_plan_active_error,
    live_plan_block_if_any,
    model_json,
    remember_decision_error,
    tool_error,
)
from mokli.trading.unified_evidence import fetch_evidence_nodes

if TYPE_CHECKING:
    from mokli.bus.queue import MessageBus

_QUOTE_PARAMETERS = tool_parameters_schema(
    symbol=StringSchema("Trading symbol (gold only, default XAUUSD)"),
    present_ui=BooleanSchema(
        description=(
            "When true, push a price-quote card to the Mokli/chat. "
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
        "(gold_decision_review, gold_analysis_committee, gold_debate_desk, "
        "gold_news_war_room, gold_mtf_panel)"
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
            "When true, push plan-status artifacts to the Mokli/chat. "
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
    return active_locale(operator_text)


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
    from mokli.trading.i18n import artifact_title

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

    _scopes = {"core"}

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
            "Get the current live gold (XAUUSD) bid/ask/mid from MetaAPI when that "
            "account is configured, otherwise from OANDA. "
            "Always use the returned mid/bid/ask — never invent prices. "
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
        try:
            require_gold(symbol)
        except GoldOnlyError as exc:
            return tool_error(REASON_POLICY_VIOLATION, instruction=str(exc))
        from mokli.trading.market_context import resolve_live_quote

        try:
            quote, source = await asyncio.to_thread(
                resolve_live_quote,
                symbol or DATA_SYMBOL,
                config,
            )
        except GoldOnlyError as exc:
            return tool_error(REASON_POLICY_VIOLATION, instruction=str(exc))
        except Exception:
            quote, source = None, "oanda"
        if quote is not None and quote.bid is not None and quote.ask is not None:
            return model_json(
                {
                    "symbol": quote.symbol,
                    "bid": quote.bid,
                    "ask": quote.ask,
                    "mid": quote.mid,
                    "tradeable": quote.tradeable,
                    "source": source,
                    "instruction": (
                        "This bid/ask is the live gold tick. "
                        "Quote it verbatim. Do not invent a price."
                    ),
                },
            )
        if not config.oanda_configured and getattr(config, "metaapi_configured", False) is not True:
            return tool_error(
                REASON_MARKET_FEED_UNCONFIGURED,
                instruction=(
                    "The platform market feed is not configured, so no live gold price is "
                    "available. Tell the operator; never quote a price from memory."
                ),
            )
        try:
            require_gold(symbol)
            payload = await fetch_evidence_nodes(["market_data"])
        except GoldOnlyError as exc:
            return tool_error(REASON_POLICY_VIOLATION, instruction=str(exc))
        except Exception as exc:
            return tool_error(
                REASON_NO_QUOTE,
                instruction="Failed to fetch the live quote; tell the operator.",
                error=str(exc),
            )
        if payload.get("aborted"):
            return tool_error(
                REASON_NO_QUOTE,
                instruction="Market data sync failed; tell the operator.",
                error=str(payload.get("abort_reason") or ""),
            )
        market = payload.get("nodes", {}).get("market_data") or {}
        display = payload.get("display") or {}
        locale = _operator_locale()
        quote_data = {
            "symbol": DATA_SYMBOL,
            "bid": market.get("quote_bid"),
            "ask": market.get("quote_ask"),
            "mid": market.get("quote_mid"),
            "tradeable": market.get("tradeable"),
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
        return model_json(
            {
                **quote_data,
                "locale": locale,
                "display": {
                    "bid": display.get("bid"),
                    "ask": display.get("ask"),
                    "mid": display.get("mid"),
                },
                "instruction": (
                    "Quote display.mid (or bid/ask) verbatim — never invent or reformat "
                    "with commas."
                ),
                "artifacts": artifacts if should_publish_trading_ui(present_ui) else [],
            },
        )


@tool_parameters(_LIVE_PLAN_PARAMETERS)
class GetLiveRecommendationTool(Tool):
    """Return the active live recommendation for this conversation."""

    _scopes = {"core"}

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
        from mokli.trading.recommendations.lifecycle import grade_session_plan

        live, quote = await grade_session_plan(session_key)
        if not live:
            return model_json(
                {
                    "has_live_plan": False,
                    "locale": locale,
                },
            )

        live_price = float(quote.mid) if quote is not None and quote.mid is not None else None
        quote_data = (
            {
                "symbol": quote.symbol,
                "bid": quote.bid,
                "ask": quote.ask,
                "mid": quote.mid,
                "tradeable": quote.tradeable,
            }
            if quote is not None and live_price is not None
            else None
        )

        outcome_status = grade_outcome_status(
            live,
            live_price=live_price,
            price_known=True,
        )
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
        return model_json(payload)


@tool_parameters(_MANAGE_PLAN_PARAMETERS)
class ManageTradingPlanTool(Tool):
    """Archive, sync, and close trading recommendations for this session."""

    _scopes = {"core"}

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
            from mokli.trading.recommendations.lifecycle import grade_session_plan

            live, _quote = await grade_session_plan(session_key)
            payload = {"ok": True, "has_live_plan": live is not None, "live_plan": live}
        elif action == "prepare_new":
            payload = await asyncio.to_thread(prepare_for_new_recommendation, session_key)
            payload["ok"] = True
        elif action == "close_plan":
            if not session_key:
                return tool_error(
                    REASON_NO_SESSION,
                    instruction="No chat session is bound; the plan cannot be closed.",
                )
            from mokli.trading.recommendations.state_machine import classify_archive_category

            bucket = classify_archive_category(close_status, close_reason="operator_close")
            payload = await asyncio.to_thread(
                close_plan_for_session,
                session_key,
                status=close_status,
                reason="operator_close",
                category=bucket,
            )
        elif action == "list_archive":
            rows = list_session_archive(session_key, category=archive_category)
            payload = {"ok": True, "archive": rows, "count": len(rows)}
        else:
            return tool_error(
                REASON_UNKNOWN_ACTION,
                instruction="Use one of: sync, prepare_new, close_plan, list_archive.",
                action=action,
            )
        payload["locale"] = locale
        payload["instruction"] = (
            "After prepare_new or closing a terminal plan, call analyze_gold "
            "(force_new_plan=true if a live plan was superseded)."
        )
        return model_json(payload)


@tool_parameters(_ANALYZE_PARAMETERS)
class AnalyzeGoldTool(Tool):
    """Run the full gold recommendation pipeline and open the side chart."""

    _scopes = {"core"}

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
            "Run a full XAUUSD gold analysis (evidence, structured decision call, G1-G20 "
            "quality gates) and issue a recommendation for this conversation. Use only when "
            "the operator asks for a new or re-evaluated recommendation / trade idea. "
            "For price-only questions use get_gold_quote. For live-plan status or follow-ups "
            "use get_live_recommendation. If a live plan already exists this returns "
            "reason_key=trading.live_plan_active instead of a second plan. "
            "team_mode=debate runs a bull/bear debate first; team_mode=swarm requires an "
            "explicit preset. If this turn already attempted a recommendation, that result is "
            "returned, including a failure, unless reevaluate or force_new_plan is set. "
            "Set present_ui=true to open the chart panel and stream cards."
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
        session_key = current_request_session_key()
        from mokli.trading.turn_session import current_turn_session

        turn = current_turn_session()
        if turn is not None and turn.decision_wire and not reevaluate and not force_new_plan:
            if should_publish_trading_ui(present_ui) and turn.kernel_result is not None:
                channel, chat_id = _request_route()
                publisher = TradingStagePublisher(
                    self._bus,
                    channel=channel,
                    chat_id=chat_id,
                    locale=_operator_locale(),
                )
                await publisher.open_chart(interval)
                await publisher.publish_result(result_to_wire(turn.kernel_result))
            return turn.decision_wire
        cached_failure = cached_decision_result(
            self.name,
            {"reevaluate": reevaluate, "force_new_plan": force_new_plan},
        )
        if cached_failure is not None:
            return cached_failure
        if team_mode in {"debate", "swarm"}:
            blocked = await live_plan_block_if_any(
                session_key,
                reevaluate=reevaluate,
                force_new_plan=force_new_plan,
            )
            if blocked is not None:
                return blocked
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
        briefing = None
        resolved_mode = team_mode or "core"
        if team_mode == "swarm" and not preset:
            return tool_error(
                REASON_PRESET_REQUIRED,
                instruction=(
                    "team_mode=swarm requires an explicit preset parameter; "
                    "pick one of the run_trading_team presets."
                ),
            )
        from mokli.agent.tools.trading_kernel import (
            cancel_synthesis_prefetch,
            finish_synthesis_prefetch,
            start_synthesis_prefetch,
        )
        # Debate and swarm briefs do not read evidence. The kernel still gathers
        # anything the overlap missed. Core mode has no team wait, so the kernel fetches.
        prefetch: asyncio.Task[None] | None = None
        if team_mode in {"debate", "swarm"} and turn is not None:
            prefetch = start_synthesis_prefetch(interval, turn)
        try:
            if team_mode == "debate":
                debate = await run_debate_crew(
                    user_message=(
                        (current_request_context().original_user_text if current_request_context() else "")
                        or ""
                    ),
                    emit=publisher.sync_emit if publish_ui else None,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher if publish_ui else None,
                    interval=interval,
                    visual_capture=visual_capture,
                    bus=self._bus,
                )
                briefing = debate.briefing
                resolved_mode = "debate"
            elif team_mode == "swarm":
                swarm = await run_swarm(
                    preset,
                    subagent_manager=self._subagent_manager,
                    publisher=publisher if publish_ui else None,
                    interval=interval,
                    emit=publisher.sync_emit if publish_ui else None,
                    visual_capture=visual_capture,
                    bus=self._bus,
                    max_review_rounds=review_round_limit(),
                )
                briefing = swarm.get("team_briefing")
                resolved_mode = f"swarm:{preset}"
            await finish_synthesis_prefetch(prefetch)
            prefetch = None
            result = await run_trading_kernel(
                interval=interval,
                team_mode=resolved_mode,
                gather_missing=True,
                reevaluate=reevaluate,
                force_new_plan=force_new_plan,
                present_ui=publish_ui,
                session_key=session_key,
                team_briefing=briefing,
                visual_capture=visual_capture,
                emit=publisher.sync_emit if publish_ui else None,
            )
        except LivePlanActive as exc:
            return remember_decision_error(live_plan_active_error(exc.live))
        except PolicyViolation as exc:
            return remember_decision_error(
                tool_error(
                    getattr(exc, "reason_key", REASON_POLICY_VIOLATION),
                    instruction=str(exc.reason),
                )
            )
        except Exception as exc:
            return remember_decision_error(
                tool_error(
                    REASON_ANALYSIS_FAILED,
                    instruction="Gold analysis failed; tell the operator and do not invent a plan.",
                    error=str(exc),
                )
            )
        finally:
            await cancel_synthesis_prefetch(prefetch)
        if result is None:
            return remember_decision_error(
                tool_error(
                    REASON_NO_RESULT,
                    instruction="Analysis produced no result; tell the operator.",
                )
            )
        wire = result_to_wire(result)
        if publish_ui:
            await publisher.publish_result(wire)
        payload = model_json(brief_for_model(wire))
        if turn is not None:
            turn.decision_wire = payload
            turn.kernel_result = result
            turn.decision_error = None
        return payload


@tool_parameters(_CAPTURE_PARAMETERS)
class CaptureGoldChartTool(Tool):
    """Capture a TradingView chart screenshot for XAUUSD."""

    _scopes = {"core"}

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
            "Capture a live XAUUSD chart screenshot from the Mokli TradingView side panel. "
            "Use when the operator asks for a chart image or screenshot without a full "
            "recommendation. Requires the Mokli chart panel to be open in the same session. "
            "Delivers the image to Telegram/WhatsApp when applicable."
        )

    async def execute(self, interval: str = "15m", **kwargs: Any) -> str:
        from mokli.trading.capture_service import chart_capture_tool_result, run_chart_capture

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
