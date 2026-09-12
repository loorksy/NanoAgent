"""Bypass LLM for high-confidence gold intents (price + analysis)."""

from __future__ import annotations

import re

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.trading.config import load_trading_config
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError
from nanobot.trading.intent_router import resolve_team_preset
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import run_swarm
from nanobot.trading.turn_planner import TurnPlan, plan_turn

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_PRICE_CONFIDENCE_MIN = 0.70
_ANALYSIS_CONFIDENCE_MIN = 0.75


def _wants_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text))


def _format_price_response(
    *,
    bid: float,
    ask: float,
    mid: float,
    tradeable: bool,
    arabic: bool,
) -> str:
    status = "tradeable" if tradeable else "non-tradeable"
    if arabic:
        return (
            f"🥇 **سعر الذهب (XAUUSD)**\n"
            f"الشراء (Bid): `{bid:.2f}`\n"
            f"البيع (Ask): `{ask:.2f}`\n"
            f"الوسط (Mid): `{mid:.2f}`\n"
            f"الحالة: {status}\n"
            f"_بيانات حية من OANDA — للتحليل الكامل اطلب «حلل الذهب»._"
        )
    return (
        f"🥇 **XAUUSD live quote**\n"
        f"Bid: `{bid:.2f}` · Ask: `{ask:.2f}` · Mid: `{mid:.2f}`\n"
        f"Status: {status}\n"
        f"_Live OANDA feed — ask me to analyze gold for a full recommendation._"
    )


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
) -> OutboundMessage | None:
    publisher = TradingStagePublisher(bus, channel=channel, chat_id=chat_id)
    interval = "15m"
    await publisher.open_chart(interval)

    try:
        if turn.mode == "team_swarm":
            preset = resolve_team_preset(text) or "gold_analysis_committee"
            if "debate" in preset:
                debate = await run_debate_crew(user_message=text, emit=publisher.sync_emit)
                result = debate.final
            else:
                swarm = await run_swarm(preset)
                result = swarm["final"]
        else:
            result = await run_unified_chart_agent(
                interval=interval,
                team_mode="core",
                emit=publisher.sync_emit,
            )
    except Exception as exc:
        body = f"Gold analysis failed: {exc}"
        if _wants_arabic(text):
            body = f"فشل تحليل الذهب: {exc}"
        return OutboundMessage(channel=channel, chat_id=chat_id, content=body)

    if result is None:
        body = "Analysis produced no result."
        if _wants_arabic(text):
            body = "لم يُنتج التحليل أي نتيجة."
        return OutboundMessage(channel=channel, chat_id=chat_id, content=body)

    wire = result_to_wire(result)
    await publisher.publish_result(wire)
    return _outbound_from_wire(wire, channel=channel, chat_id=chat_id)


async def try_gold_fast_path(
    message: str,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None = None,
) -> OutboundMessage | None:
    """Return an immediate gold response for confident price or analysis intents."""
    text = (message or "").strip()
    if not text:
        return None

    turn = plan_turn(text)

    if turn.mode == "market_data_only":
        if turn.intent.confidence < _PRICE_CONFIDENCE_MIN:
            return None
        config = load_trading_config()
        if not config.oanda_configured:
            body = (
                "OANDA is not configured — cannot fetch the live gold quote."
                if not _wants_arabic(text)
                else "OANDA غير مُعدّ — لا يمكن جلب سعر الذهب الحي."
            )
            return OutboundMessage(channel=channel, chat_id=chat_id, content=body)

        try:
            quote = fetch_quote(DATA_SYMBOL, config=config)
        except GoldOnlyError as exc:
            return OutboundMessage(channel=channel, chat_id=chat_id, content=str(exc))
        except Exception as exc:
            body = f"Failed to fetch gold quote: {exc}"
            return OutboundMessage(channel=channel, chat_id=chat_id, content=body)

        if quote is None:
            body = "No quote returned from OANDA."
            return OutboundMessage(channel=channel, chat_id=chat_id, content=body)

        content = _format_price_response(
            bid=quote.bid,
            ask=quote.ask,
            mid=quote.mid,
            tradeable=quote.tradeable,
            arabic=_wants_arabic(text),
        )
        return OutboundMessage(channel=channel, chat_id=chat_id, content=content)

    if turn.mode in ("full_analysis", "team_swarm"):
        if turn.intent.confidence < _ANALYSIS_CONFIDENCE_MIN:
            return None
        config = load_trading_config()
        if not config.oanda_configured:
            body = (
                "OANDA is not configured — cannot run gold analysis."
                if not _wants_arabic(text)
                else "OANDA غير مُعدّ — لا يمكن تشغيل تحليل الذهب."
            )
            return OutboundMessage(channel=channel, chat_id=chat_id, content=body)
        return await _run_analysis_fast_path(
            turn,
            text,
            channel=channel,
            chat_id=chat_id,
            bus=bus,
        )

    return None
