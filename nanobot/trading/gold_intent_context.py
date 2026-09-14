"""Lightweight gold context for the conversational agent (no keyword routing)."""

from __future__ import annotations

from nanobot.agent.tools.context import RequestContext
from nanobot.runtime_context import RuntimeContextBlock, wrap_runtime_context_lines
from nanobot.trading.config import load_trading_config
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.store import latest_live_recommendation


def _plain_price(value: object | None) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return None


async def gold_intent_runtime_context(
    request: RequestContext,
) -> RuntimeContextBlock | None:
    """Tell the LLM when a live plan exists and inject fresh platform prices."""
    text = (request.original_user_text or "").strip()
    if not text:
        return None
    live = latest_live_recommendation(request.session_key)
    if not live:
        return None

    direction = str(live.get("direction") or "wait").upper()
    lines = [
        f"A live {direction} XAUUSD recommendation is on file for this conversation.",
        "Interpret the operator's message and choose trading tools accordingly.",
        "One live recommendation per conversation — do not issue a second plan while active.",
        "For status or price follow-ups, call get_live_recommendation (or get_gold_quote for price only).",
        "Copy exact numeric prices from tool JSON in replies — gold trades near 4300+, never 3300-range.",
    ]

    entry = _plain_price(live.get("entry"))
    stop = _plain_price(live.get("stop_loss"))
    targets = [_plain_price(t) for t in list(live.get("targets") or [])[:2]]
    if entry:
        level_bits = [f"entry={entry}"]
        if stop:
            level_bits.append(f"stop={stop}")
        if targets:
            level_bits.append("targets=" + "/".join(t for t in targets if t))
        lines.append("Stored plan levels (plain): " + ", ".join(level_bits))

    config = load_trading_config()
    if config.oanda_configured:
        try:
            quote = fetch_quote(DATA_SYMBOL, config=config)
            if quote and quote.mid is not None:
                lines.append(f"Platform live XAUUSD mid now: {_plain_price(quote.mid)}")
        except Exception:
            pass

    if request.channel == "websocket":
        from nanobot.agent.delivery_targets import default_telegram_chat_id

        tg_chat = default_telegram_chat_id()
        if tg_chat:
            lines.append(
                f"Operator Telegram delivery id (for message tool): {tg_chat}. "
                "Never use the WebUI session UUID as a Telegram chat_id."
            )

    if request.channel in ("telegram", "whatsapp"):
        lines.append(
            "When a trading tool already delivered the recommendation card, "
            "acknowledge briefly without repeating entry, stop, or targets."
        )
    return RuntimeContextBlock(
        source="gold_intent",
        content=wrap_runtime_context_lines(lines),
    )
