"""Choose which prompt layers a turn actually needs.

Durable identity stays. Long-term memory and the skills catalog are task
layers: a short message that is not about trading, memory, or a strategy
does not reload them. Conversation history and fresh tool output stay on
their own path in the runner.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

# A short greeting or a one-line question has no trading or memory job.
_TASK_MARKERS = re.compile(
    r"ذهب|الذهب|gold|xau|تحليل|استراتيج|strategy|backtest|صفقة|توصية|"
    r"خبر|أخبار|news|macro|ذاكرة|تذكر|تابع|أكمل|اكمل|continue|remember",
    re.IGNORECASE,
)
_SHORT_TURN_CHARS = 280


@dataclass(frozen=True, slots=True)
class ContextLayers:
    include_memory: bool
    include_skills: bool


# Light turns expose only general chat/search tools to the provider; trading and
# filesystem tools stay registered for the next task-shaped message.
_LIGHT_PROVIDER_TOOLS = frozenset({"message", "web_search", "web_fetch"})
# Session routing tools stay available on light turns (transient chats, no trading job).
_SESSION_PROVIDER_TOOLS = frozenset({
    "list_sessions",
    "read_session",
    "search_sessions",
    "send_session_message",
})
_LIGHT_ALLOWED_PROVIDER_TOOLS = _LIGHT_PROVIDER_TOOLS | _SESSION_PROVIDER_TOOLS

# Legacy blacklist kept for tests/docs; light turns use the whitelist above.
_DEFERRED_PROVIDER_TOOLS = frozenset({
    "analyze_gold",
    "capture_gold_chart",
    "fast_backtest",
    "fetch_evidence",
    "get_gate_report",
    "get_gold_quote",
    "get_live_recommendation",
    "gold_intel_scan",
    "manage_trading_plan",
    "mt5_cancel_order",
    "mt5_close_position",
    "mt5_confirm_order",
    "mt5_get_account",
    "mt5_list_symbols",
    "mt5_market",
    "mt5_modify_order",
    "mt5_propose_order",
    "propose_strategy",
    "run_trading_kernel",
    "run_trading_team",
    "spawn",
})


def provider_tool_names_for_layers(
    registered: Sequence[str],
    layers: ContextLayers,
) -> list[str]:
    """Tool names sent to the provider on this turn (subset on light turns)."""
    if layers.include_skills:
        return list(registered)
    return [name for name in registered if name in _LIGHT_ALLOWED_PROVIDER_TOOLS]


def layers_for_task(text: str | None) -> ContextLayers:
    body = (text or "").strip()
    if not body or len(body) > _SHORT_TURN_CHARS or _TASK_MARKERS.search(body):
        return ContextLayers(include_memory=True, include_skills=True)
    return ContextLayers(include_memory=False, include_skills=False)


def layers_for_archived_history(history: Sequence[object]) -> ContextLayers:
    """Match task layers to the last user turn being archived, not an empty tail."""
    for message in reversed(history):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user" or message.get("_command"):
            continue
        content = message.get("content")
        if isinstance(content, str):
            return layers_for_task(content)
    return layers_for_task(None)


def layers_for_transcript_boundary(
    *,
    current_message: str | None,
    history: Sequence[object],
    prompt_layers: ContextLayers | None = None,
) -> ContextLayers:
    """Resolve prompt layers for a transcript rebuild or archive boundary."""
    if prompt_layers is not None:
        return prompt_layers
    if current_message is not None:
        return layers_for_task(current_message)
    if history:
        return layers_for_archived_history(history)
    return layers_for_task(None)
