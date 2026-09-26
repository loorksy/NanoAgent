"""Structured, instructive error payloads returned by trading tools.

A trading tool is always registered. When it cannot run in the current state it
returns ``{"ok": false, "reason_key": ...}`` so the agent can explain the block
and pick the next tool, instead of the tool silently not existing.
"""

from __future__ import annotations

import json
from typing import Any

from mokli.agent.tools.base import ToolResult

REASON_LIVE_PLAN_ACTIVE = "trading.live_plan_active"
REASON_PLAN_CLOSE_FAILED = "trading.plan_close_failed"
REASON_MARKET_FEED_UNCONFIGURED = "trading.market_feed_unconfigured"
REASON_NO_QUOTE = "trading.no_live_quote"
REASON_NO_SESSION = "trading.no_chat_session"
REASON_PRESET_REQUIRED = "trading.team_preset_required"
REASON_POLICY_VIOLATION = "trading.policy_violation"
REASON_ANALYSIS_FAILED = "trading.analysis_failed"
REASON_TEAM_FAILED = "trading.team_failed"
REASON_NO_RESULT = "trading.no_result"
REASON_UNKNOWN_ACTION = "trading.unknown_action"


def tool_error(reason_key: str, *, instruction: str, **details: Any) -> ToolResult:
    """Build an error ``ToolResult`` whose body is machine-readable JSON.

    ``instruction`` tells the LLM what to do next; ``reason_key`` is the stable
    key clients and the locale catalog use to render the operator-facing text.
    """
    payload: dict[str, Any] = {"ok": False, "reason_key": reason_key, **details}
    payload["instruction"] = instruction
    return ToolResult.error(json.dumps(payload, indent=2, default=str))


def live_plan_active_error(live: dict[str, Any]) -> ToolResult:
    """One live plan per conversation — returned instead of running the kernel."""
    return tool_error(
        REASON_LIVE_PLAN_ACTIVE,
        instruction=(
            "This conversation already has a live recommendation, so no second plan "
            "was issued. Explain this to the operator. For status or price follow-ups "
            "call get_live_recommendation; to archive it call manage_trading_plan "
            "(action=close_plan); only when the operator explicitly confirms a "
            "replacement, call analyze_gold again with force_new_plan=true."
        ),
        live_plan={
            "id": str(live.get("id") or ""),
            "direction": str(live.get("direction") or "wait"),
            "entry": live.get("entry"),
            "stop_loss": live.get("stop_loss"),
            "targets": list(live.get("targets") or []),
            "status": live.get("status"),
        },
        next_tools=["get_live_recommendation", "manage_trading_plan"],
    )
