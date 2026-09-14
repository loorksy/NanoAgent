"""Lightweight gold context for the conversational agent (no keyword routing)."""

from __future__ import annotations

from nanobot.agent.tools.context import RequestContext
from nanobot.runtime_context import RuntimeContextBlock, wrap_runtime_context_lines
from nanobot.trading.recommendations.store import latest_live_recommendation


async def gold_intent_runtime_context(
    request: RequestContext,
) -> RuntimeContextBlock | None:
    """Tell the LLM when a live plan exists; tool choice stays with the agent."""
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
    ]
    if request.channel in ("telegram", "whatsapp"):
        lines.append(
            "When a trading tool already delivered the recommendation card, "
            "acknowledge briefly without repeating entry, stop, or targets."
        )
    return RuntimeContextBlock(
        source="gold_intent",
        content=wrap_runtime_context_lines(lines),
    )
