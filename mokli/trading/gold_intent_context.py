"""Lightweight gold context for the conversational agent (no keyword routing)."""

from __future__ import annotations

from mokli.agent.tools.context import RequestContext
from mokli.runtime_context import RuntimeContextBlock, wrap_runtime_context_lines
from mokli.trading.decision_route import is_gold_decision_question
from mokli.trading.recommendations.lifecycle import grade_session_plan


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
    """Tell the LLM when a live plan exists.

    A live row is graded with one quote read off the event loop. The tick is
    not copied into the prompt; a price follow-up calls get_gold_quote.
    """
    text = (request.original_user_text or "").strip()
    if not text:
        return None
    live, _quote = await grade_session_plan(request.session_key)
    if not live:
        if not is_gold_decision_question(text):
            return None
        return RuntimeContextBlock(
            source="gold_intent",
            content=wrap_runtime_context_lines(
                [
                    "The operator asked for a gold buy/sell decision.",
                    "The runtime runs run_trading_kernel with decision_review=true before you answer.",
                    "That runs gold_decision_review, then the kernel. The kernel is the only BUY/SELL path.",
                    "Use the tool result already in this turn. Do not call the kernel again.",
                ]
            ),
        )

    direction = str(live.get("direction") or "wait").upper()
    lines = [
        f"A live {direction} XAUUSD recommendation is on file for this conversation.",
        "Interpret the operator's message and choose trading tools accordingly.",
        "One live recommendation per conversation — do not issue a second plan while active.",
        "When outcome_status is invalidated/tp1/expired, the plan is closed automatically — "
        "you may call analyze_gold for a fresh recommendation.",
        "For status or price follow-ups, call get_live_recommendation (or get_gold_quote for price only).",
        "Copy exact numeric prices from tool JSON in replies; never quote prices from memory.",
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

    if request.channel == "websocket":
        from mokli.agent.delivery_targets import default_telegram_chat_id

        tg_chat = default_telegram_chat_id()
        if tg_chat:
            lines.append(
                f"Operator Telegram delivery id (for message tool): {tg_chat}. "
                "Never use the Mokli session UUID as a Telegram chat_id."
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
