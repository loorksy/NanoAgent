"""Phase J — dynamic executor for light turn paths."""

from __future__ import annotations

from typing import Any

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.trading.cards.artifacts import apply_result_artifacts, build_price_quote_artifacts
from nanobot.trading.chart_capture import resolve_visual_capture
from nanobot.trading.config import load_trading_config
from nanobot.trading.evidence import PipelineContext, is_light_path_mode, run_evidence_graph
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError
from nanobot.trading.i18n import label_map, tr
from nanobot.trading.locale import locale_from_text
from nanobot.trading.policy_guard import log_planner_shadow, validate_turn_plan
from nanobot.trading.recommendations.followup import (
    explain_new_rec_blocked,
    grade_live_recommendation,
)
from nanobot.trading.recommendations.gate_report import build_gate_report_result
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.types import AgentFinalResult
from nanobot.trading.turn_planner import TurnPlan

_PRICE_CONFIDENCE_MIN = 0.70
_CHART_CONFIDENCE_MIN = 0.75


def _format_price_response(
    *,
    bid: float,
    ask: float,
    mid: float,
    tradeable: bool,
    locale: str,
) -> str:
    labels = label_map("card", locale)
    status = labels["tradeable"] if tradeable else labels["non_tradeable"]
    return (
        f"🥇 **{tr('price.header', locale)}**\n"
        f"{labels['bid']}: `{bid:.2f}`\n"
        f"{labels['ask']}: `{ask:.2f}`\n"
        f"{labels['mid']}: `{mid:.2f}`\n"
        f"{labels['state']}: {status}\n"
        f"_{tr('price.footer', locale)}_"
    )


def _quote_from_market(market: Any) -> dict[str, Any] | None:
    if market.quote_mid is None:
        return None
    bid = market.quote_bid if market.quote_bid is not None else market.quote_mid
    ask = market.quote_ask if market.quote_ask is not None else market.quote_mid
    return {
        "symbol": market.symbol,
        "bid": bid,
        "ask": ask,
        "mid": market.quote_mid,
        "tradeable": market.tradeable,
    }


async def _run_validated_evidence(
    turn: TurnPlan,
    *,
    interval: str = "15m",
    visual_capture: Any | None = None,
    track: Any | None = None,
) -> PipelineContext:
    config = load_trading_config()
    validated = validate_turn_plan(turn, shadow_mode=config.planner_shadow_mode)
    log_planner_shadow(validated)
    ctx = PipelineContext(
        symbol=DATA_SYMBOL,
        interval=interval,
        visual_capture=visual_capture,
    )
    return await run_evidence_graph(ctx, validated.executed_graph, track=track)


async def _execute_price_path(
    turn: TurnPlan,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None,
    text: str,
) -> OutboundMessage | None:
    if turn.intent.confidence < _PRICE_CONFIDENCE_MIN:
        return None

    locale = locale_from_text(text)
    config = load_trading_config()
    if not config.oanda_configured:
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("price.feed_unconfigured", locale),
        )

    try:
        pipeline = await _run_validated_evidence(turn)
    except GoldOnlyError as exc:
        return OutboundMessage(channel=channel, chat_id=chat_id, content=str(exc))
    except Exception as exc:
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("price.fetch_failed", locale, error=exc),
        )

    if pipeline.aborted or pipeline.market is None or not pipeline.market.sync.ok:
        reason = pipeline.abort_reason or (
            pipeline.market.sync.reason if pipeline.market else "Market data sync failed"
        )
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("price.fetch_failed", locale, error=reason),
        )

    quote_data = _quote_from_market(pipeline.market)
    if quote_data is None:
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("price.no_quote", locale),
        )

    content = _format_price_response(
        bid=float(quote_data["bid"]),
        ask=float(quote_data["ask"]),
        mid=float(quote_data["mid"]),
        tradeable=bool(quote_data["tradeable"]),
        locale=locale,
    )
    artifacts = build_price_quote_artifacts(quote_data, locale=locale)
    if bus is not None:
        publisher = TradingStagePublisher(
            bus, channel=channel, chat_id=chat_id, locale=locale,
        )
        await publisher.publish_artifacts(artifacts, locale=locale)
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=content,
        metadata={
            OUTBOUND_META_AGENT_UI: {
                "kind": "trading_artifacts",
                "data": {"artifacts": artifacts, "locale": locale},
            }
        },
    )


async def _execute_chart_capture_path(
    turn: TurnPlan,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None,
    text: str,
) -> OutboundMessage | None:
    if turn.intent.confidence < _CHART_CONFIDENCE_MIN:
        return None

    from nanobot.trading.capture_service import run_chart_capture

    config = load_trading_config()
    validated = validate_turn_plan(turn, shadow_mode=config.planner_shadow_mode)
    log_planner_shadow(validated)

    payload = await run_chart_capture(
        bus=bus,
        channel=channel,
        chat_id=chat_id,
        operator_text=text,
    )
    if not payload.get("ok"):
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=str(payload.get("message") or "Chart capture failed."),
        )
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=str(payload.get("artifacts", [{}])[0].get("title") or "Chart captured."),
        metadata={
            OUTBOUND_META_AGENT_UI: {
                "kind": "trading_artifacts",
                "data": {
                    "artifacts": payload.get("artifacts") or [],
                    "locale": payload.get("locale"),
                },
            }
        },
    )


async def _execute_followup_path(
    turn: TurnPlan,
    *,
    channel: str,
    chat_id: str,
    text: str,
    live: dict | None,
) -> OutboundMessage:
    locale = locale_from_text(text)
    live_price: float | None = None

    if turn.nodes:
        try:
            pipeline = await _run_validated_evidence(turn)
            if pipeline.market and pipeline.market.quote_mid is not None:
                live_price = pipeline.market.quote_mid
        except Exception:
            live_price = None

    if turn.requested_new_plan:
        graded = explain_new_rec_blocked(live, operator_text=text, live_price=live_price)
    else:
        graded = grade_live_recommendation(live, operator_text=text, live_price=live_price)
    result = AgentFinalResult(
        decision=graded,
        team_mode="followup",
        recommendation_id=str((live or {}).get("id") or ""),
    )
    apply_result_artifacts(
        result,
        operator_text=text,
        intent_kind="recommendation_followup",
        locale=locale,
        followup=True,
        plan_row=live,
    )
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=graded.summary,
        metadata={
            OUTBOUND_META_AGENT_UI: {
                "kind": "trading_artifacts",
                "data": {"artifacts": result.artifacts, "locale": locale},
            }
        }
        if result.artifacts
        else {},
    )


async def execute_gate_report_path(
    turn: TurnPlan,
    *,
    text: str,
    channel: str,
    chat_id: str,
    live: dict | None,
) -> OutboundMessage:
    locale = locale_from_text(text)
    result = build_gate_report_result(live, operator_text=text, locale=locale)
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=result.decision.summary,
        metadata={
            OUTBOUND_META_AGENT_UI: {
                "kind": "trading_artifacts",
                "data": {"artifacts": result.artifacts, "locale": locale},
            }
        }
        if result.artifacts
        else {},
    )


async def execute_light_path(
    turn: TurnPlan,
    *,
    text: str,
    channel: str,
    chat_id: str,
    bus: MessageBus | None = None,
    live: dict | None = None,
) -> OutboundMessage | None:
    """Execute a validated light-path turn plan (price, chart, follow-up)."""
    if not is_light_path_mode(turn.mode):
        return None

    if turn.mode == "market_data_only":
        return await _execute_price_path(
            turn,
            channel=channel,
            chat_id=chat_id,
            bus=bus,
            text=text,
        )
    if turn.mode == "chart_capture":
        return await _execute_chart_capture_path(
            turn,
            channel=channel,
            chat_id=chat_id,
            bus=bus,
            text=text,
        )
    if turn.mode == "recommendation_followup":
        return await _execute_followup_path(
            turn,
            channel=channel,
            chat_id=chat_id,
            text=text,
            live=live,
        )
    return None
