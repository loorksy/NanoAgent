"""Bypass LLM for high-confidence gold intents (price + analysis)."""

from __future__ import annotations

from typing import Any

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.trading.config import load_trading_config
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.evidence import is_light_path_mode
from nanobot.trading.intent_router import resolve_team_preset
from nanobot.agent.tools.context import current_request_context
from nanobot.trading.chart_capture import resolve_visual_capture
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.teams.runtime import run_swarm
from nanobot.trading.recommendations.store import latest_live_recommendation
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.i18n import tr
from nanobot.trading.locale import locale_from_text
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.turn_executor import execute_gate_report_path, execute_light_path
from nanobot.trading.turn_planner import TurnPlan, plan_turn

_ANALYSIS_CONFIDENCE_MIN = 0.75


def _outbound_from_wire(
    wire: dict,
    *,
    channel: str,
    chat_id: str,
) -> OutboundMessage:
    decision = str(wire.get("decision", "wait")).upper()
    summary = str(wire.get("summary", ""))
    content = f"{decision}: {summary}" if summary else decision
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=content,
        metadata={
            OUTBOUND_META_AGENT_UI: {
                "kind": "trading_result",
                "data": wire,
            }
        },
    )


async def _run_analysis_fast_path(
    turn: TurnPlan,
    text: str,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None,
    subagent_manager: Any | None = None,
) -> OutboundMessage | None:
    locale = locale_from_text(text)
    publisher = TradingStagePublisher(
        bus, channel=channel, chat_id=chat_id, locale=locale,
    )
    interval = "15m"
    await publisher.open_chart(interval)
    visual_capture = resolve_visual_capture(publisher)

    try:
        if turn.mode == "team_swarm":
            preset = resolve_team_preset(text) or "gold_analysis_committee"
            if "debate" in preset:
                debate = await run_debate_crew(
                    user_message=text,
                    emit=publisher.sync_emit,
                    subagent_manager=subagent_manager,
                    publisher=publisher,
                    interval=interval,
                    visual_capture=visual_capture,
                )
                result = debate.final
            else:
                swarm = await run_swarm(
                    preset,
                    subagent_manager=subagent_manager,
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
                turn_plan=turn,
            )
    except Exception as exc:
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("analysis.failed", locale, error=exc),
        )

    if result is None:
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=tr("analysis.no_result", locale),
        )

    wire = result_to_wire(result)
    wire["locale"] = locale
    await publisher.publish_result(wire, include_card=False)
    if channel == "telegram":
        from nanobot.channels.telegram.trading_cards import render_recommendation_card

        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=render_recommendation_card(wire, locale=locale),
            metadata={"parse_mode": "HTML"},
        )
    if channel == "whatsapp":
        from nanobot.channels.whatsapp.trading_cards import render_recommendation_card

        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=render_recommendation_card(wire, locale=locale),
        )
    return _outbound_from_wire(wire, channel=channel, chat_id=chat_id)


async def try_gold_fast_path(
    message: str,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None = None,
    subagent_manager: Any | None = None,
) -> OutboundMessage | None:
    """Return an immediate gold response for confident price or analysis intents."""
    text = (message or "").strip()
    if not text:
        return None

    ctx = current_request_context()
    session_key = (ctx.session_key if ctx else None) or f"{channel}:{chat_id}"
    live = latest_live_recommendation(session_key)
    turn = plan_turn(text, active_recommendation_live=bool(live))

    if turn.mode == "gate_report":
        return await execute_gate_report_path(
            turn,
            text=text,
            channel=channel,
            chat_id=chat_id,
            live=live,
        )

    if is_light_path_mode(turn.mode):
        return await execute_light_path(
            turn,
            text=text,
            channel=channel,
            chat_id=chat_id,
            bus=bus,
            live=live,
        )

    if turn.mode in ("full_analysis", "team_swarm"):
        if turn.intent.kind != "recommendation" and turn.intent.confidence < _ANALYSIS_CONFIDENCE_MIN:
            return None
        config = load_trading_config()
        if not config.oanda_configured:
            locale = locale_from_text(text)
            return OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=tr("analysis.feed_unconfigured", locale),
            )
        return await _run_analysis_fast_path(
            turn,
            text,
            channel=channel,
            chat_id=chat_id,
            bus=bus,
            subagent_manager=subagent_manager,
        )

    return None
