"""Inject gold trading intent hints into the agent turn context."""

from __future__ import annotations

from nanobot.agent.tools.context import RequestContext
from nanobot.runtime_context import RuntimeContextBlock, wrap_runtime_context_lines
from nanobot.trading.recommendations.store import latest_live_recommendation
from nanobot.trading.turn_planner import TurnPlan, plan_turn

_MODE_TOOL_HINTS: dict[str, str] = {
    "market_data_only": "Use get_gold_quote for the live XAUUSD price.",
    "full_analysis": "Use analyze_gold for a full recommendation with chart and stages.",
    "team_swarm": (
        "Use run_trading_team with the matching preset, or analyze_gold with "
        "team_mode=swarm/debate."
    ),
    "recommendation_followup": (
        "A live recommendation already exists. Do not mint a second plan. "
        "Call analyze_gold only to grade the live plan (follow-up)."
    ),
    "conversation": "",
    "specialist": "",
}


def gold_intent_plan(message: str, *, session_key: str | None = None) -> TurnPlan:
    live = latest_live_recommendation(session_key)
    return plan_turn(message, active_recommendation_live=bool(live))


async def gold_intent_runtime_context(
    request: RequestContext,
) -> RuntimeContextBlock | None:
    text = (request.original_user_text or "").strip()
    if not text:
        return None
    live = latest_live_recommendation(request.session_key)
    turn = plan_turn(text, active_recommendation_live=bool(live))
    if turn.mode == "conversation":
        return None
    tool_hint = _MODE_TOOL_HINTS.get(turn.mode, "")
    lines = [
        f"Detected gold intent: {turn.intent.kind} ({turn.intent.reason}, "
        f"confidence={turn.intent.confidence:.2f}).",
        f"Turn mode: {turn.mode}.",
    ]
    if tool_hint:
        lines.append(tool_hint)
    if turn.emit_stages:
        lines.append("Stream analysis stages to the user when running tools.")
    if request.channel in ("telegram", "whatsapp"):
        lines.append(
            "The trading tool already delivers the recommendation card to the user. "
            "Do not repeat entry, stop, or targets. Do not mention a chart panel. "
            "A short acknowledgment is enough."
        )
    return RuntimeContextBlock(
        source="gold_intent",
        content=wrap_runtime_context_lines(lines),
    )
