"""Inject gold trading intent hints into the agent turn context."""

from __future__ import annotations

from nanobot.agent.tools.context import RequestContext
from nanobot.runtime_context import RuntimeContextBlock, wrap_runtime_context_lines
from nanobot.trading.turn_planner import TurnPlan, plan_turn

_MODE_TOOL_HINTS: dict[str, str] = {
    "market_data_only": "Use get_gold_quote for the live XAUUSD price.",
    "full_analysis": (
        "Use analyze_gold for a full recommendation with chart and stages. "
        "For committee/debate/swarm requests use run_trading_team."
    ),
    "team_swarm": "Use run_trading_team with the matching gold preset.",
    "general_chat": "",
}


def gold_intent_plan(message: str) -> TurnPlan:
    return plan_turn(message)


async def gold_intent_runtime_context(
    request: RequestContext,
) -> RuntimeContextBlock | None:
    text = (request.original_user_text or "").strip()
    if not text:
        return None
    turn = plan_turn(text)
    if turn.mode == "general_chat":
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
    return RuntimeContextBlock(
        source="gold_intent",
        content=wrap_runtime_context_lines(lines),
    )
