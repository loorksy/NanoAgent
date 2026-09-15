"""Recommendation lifecycle — sync outcomes, archive closed plans, agent operations."""

from __future__ import annotations

from typing import Any, Literal

from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.followup import finalize_live_plan_if_closed, grade_outcome_status
from nanobot.trading.recommendations.state_machine import (
    CLOSED_OUTCOME_STATUSES,
    classify_archive_category,
    is_closed_status,
)
from nanobot.trading.recommendations.store import (
    archive_recommendation,
    close_live_recommendation,
    get_recommendation,
    latest_live_recommendation,
    list_archived_recommendations,
    update_recommendation_status,
)

ArchiveCategory = Literal[
    "invalidated",
    "win",
    "loss",
    "modified",
    "superseded",
    "expired",
    "other",
]


def resolve_live_price(live_price: float | None = None) -> float | None:
    if live_price is not None:
        return live_price
    try:
        quote = fetch_quote(DATA_SYMBOL)
        return quote.mid if quote else None
    except Exception:
        return None


def sync_session_live_plan(
    session_key: str | None,
    *,
    live_price: float | None = None,
) -> dict[str, Any] | None:
    """Grade the session's live row against price and persist terminal outcomes."""
    if not session_key:
        return None
    live = latest_live_recommendation(session_key)
    if not live:
        return None
    price = resolve_live_price(live_price)
    remaining = finalize_live_plan_if_closed(live, live_price=price)
    if remaining is None:
        return latest_live_recommendation(session_key)
    graded = grade_outcome_status(remaining, live_price=price)
    if graded != str(remaining.get("status") or ""):
        update_recommendation_status(str(remaining["id"]), graded)
        remaining = {**remaining, "status": graded}
    if is_closed_status(graded):
        archive_recommendation(
            str(remaining["id"]),
            category=classify_archive_category(graded),
            reason=graded,
        )
        return None
    return remaining


def close_plan_for_session(
    session_key: str,
    *,
    status: str = "superseded",
    reason: str = "operator_request",
    category: ArchiveCategory | None = None,
) -> dict[str, Any]:
    live = sync_session_live_plan(session_key)
    if not live:
        return {"ok": False, "error": "no_live_recommendation"}
    rec_id = str(live["id"])
    bucket = category or classify_archive_category(status, close_reason=reason)
    closed = close_live_recommendation(rec_id, status=status, reason=reason)
    if not closed:
        update_recommendation_status(rec_id, status)
    archive_recommendation(rec_id, category=bucket, reason=reason)
    return {"ok": True, "recommendation_id": rec_id, "status": status, "archive_category": bucket}


def prepare_for_new_recommendation(
    session_key: str | None,
    *,
    live_price: float | None = None,
    force_close_invalidated: bool = True,
) -> dict[str, Any]:
    """Ensure a closed terminal plan does not block a new analysis."""
    if not session_key:
        return {"ok": True, "live_plan": None, "action": "none"}
    live = sync_session_live_plan(session_key, live_price=live_price)
    if live:
        price = resolve_live_price(live_price)
        graded = grade_outcome_status(live, live_price=price)
        if force_close_invalidated and graded in CLOSED_OUTCOME_STATUSES:
            result = close_plan_for_session(
                session_key,
                status=graded,
                reason=f"auto_close_{graded}",
                category=classify_archive_category(graded),
            )
            result["action"] = "auto_archived"
            result["live_plan"] = None
            return result
        return {"ok": True, "live_plan": live, "action": "live_remains"}
    return {"ok": True, "live_plan": None, "action": "already_clear"}


def list_session_archive(
    session_key: str | None,
    *,
    category: ArchiveCategory | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not session_key:
        return []
    return list_archived_recommendations(session_key, category=category, limit=limit)


def get_plan_row(rec_id: str) -> dict[str, Any] | None:
    return get_recommendation(rec_id)
