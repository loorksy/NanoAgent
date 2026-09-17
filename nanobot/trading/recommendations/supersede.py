"""In-session recommendation supersede (approve new / reject)."""

from __future__ import annotations

import time
from typing import Any, Literal

from nanobot.trading.recommendations.store import (
    close_live_recommendation,
    get_recommendation,
    latest_live_recommendation,
)

SupersedeAction = Literal["approve_new", "reject_new"]

_PENDING: dict[str, dict[str, Any]] = {}


def mark_supersede_pending(session_key: str, live: dict[str, Any]) -> None:
    _PENDING[session_key] = {
        "recommendation_id": str(live.get("id") or ""),
        "requested_at": int(time.time() * 1000),
        "live": dict(live),
    }


def clear_supersede_pending(session_key: str) -> None:
    _PENDING.pop(session_key, None)


def pending_supersede(session_key: str) -> dict[str, Any] | None:
    return _PENDING.get(session_key)


def apply_supersede_transition(
    session_key: str,
    *,
    recommendation_id: str,
    action: SupersedeAction,
) -> dict[str, Any]:
    live = latest_live_recommendation(session_key)
    if live is None:
        clear_supersede_pending(session_key)
        return {"ok": False, "error": "no_live_recommendation"}
    live_id = str(live.get("id") or "")
    if recommendation_id and recommendation_id != live_id:
        return {"ok": False, "error": "recommendation_mismatch"}
    if action == "reject_new":
        clear_supersede_pending(session_key)
        return {
            "ok": True,
            "kept": get_recommendation(live_id),
            "session_state": "idle",
        }
    closed = close_live_recommendation(live_id, status="superseded", reason="user_superseded")
    clear_supersede_pending(session_key)
    if not closed:
        return {"ok": False, "error": "close_failed"}
    from nanobot.trading.recommendations.store import archive_recommendation

    archive_recommendation(live_id, category="superseded", reason="user_superseded")
    return {
        "ok": True,
        "closed_recommendation": get_recommendation(live_id),
        "session_state": "ready_for_new",
    }
