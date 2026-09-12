"""Bypass LLM for high-confidence gold price queries."""

from __future__ import annotations

import re

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.trading.config import load_trading_config
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.turn_planner import plan_turn

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_PRICE_CONFIDENCE_MIN = 0.70


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


async def try_gold_fast_path(
    message: str,
    *,
    channel: str,
    chat_id: str,
    bus: MessageBus | None = None,
) -> OutboundMessage | None:
    """Return an immediate price response when intent is a confident price query."""
    text = (message or "").strip()
    if not text:
        return None

    turn = plan_turn(text)
    if turn.mode != "market_data_only":
        return None
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
