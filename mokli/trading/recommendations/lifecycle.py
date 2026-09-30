"""Recommendation lifecycle — sync outcomes, archive closed plans, agent operations."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from mokli.trading.gold import DATA_SYMBOL
from mokli.trading.oanda import OandaQuote
from mokli.trading.recommendations.followup import (
    finalize_live_plan_if_closed,
    grade_outcome_status,
)
from mokli.trading.recommendations.state_machine import (
    CLOSED_OUTCOME_STATUSES,
    classify_archive_category,
    is_closed_status,
)
from mokli.trading.recommendations.store import (
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
        from mokli.trading.market_context import resolve_live_quote

        quote, _source = resolve_live_quote(DATA_SYMBOL)
        return quote.mid if quote else None
    except Exception:
        return None


async def blocking_live_plan(
    session_key: str | None,
    *,
    reevaluate: bool = False,
    force_new_plan: bool = False,
) -> dict[str, Any] | None:
    """Grade once and return a row that still blocks a new plan.

    ``reevaluate`` and ``force_new_plan`` are the kernel's own overrides, so
    this returns None and does not download. No stored row means no download.
    """
    if reevaluate or force_new_plan or not session_key:
        return None
    live, _quote = await grade_session_plan(session_key)
    return live


async def grade_session_plan(
    session_key: str | None,
) -> tuple[dict[str, Any] | None, OandaQuote | None]:
    """Grade a live plan with one quote read off the event loop.

    No live row means no download. The quote is returned so a caller can show
    the same tick it graded with, instead of fetching again.
    """
    if not session_key or latest_live_recommendation(session_key) is None:
        return None, None
    from mokli.trading.market_context import resolve_live_quote

    quote, _source = await asyncio.to_thread(resolve_live_quote, DATA_SYMBOL)
    mid = quote.mid if quote is not None else None
    live = sync_session_live_plan(session_key, live_price=mid, price_known=True)
    return live, quote


def sync_session_live_plan(
    session_key: str | None,
    *,
    live_price: float | None = None,
    price_known: bool = False,
) -> dict[str, Any] | None:
    """Grade the session's live row against price and persist terminal outcomes.

    ``price_known`` means the caller already tried to read the live quote.
    A missing price then stays missing instead of starting a second download.
    """
    if not session_key:
        return None
    live = latest_live_recommendation(session_key)
    if not live:
        return None
    if not price_known:
        price = resolve_live_price(live_price)
        price_known = True
    else:
        price = live_price
    remaining = finalize_live_plan_if_closed(live, live_price=price, price_known=price_known)
    if remaining is None:
        return latest_live_recommendation(session_key)
    graded = grade_outcome_status(remaining, live_price=price, price_known=price_known)
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
    live_price: float | None = None,
    price_known: bool = False,
) -> dict[str, Any]:
    live = sync_session_live_plan(
        session_key,
        live_price=live_price,
        price_known=price_known,
    )
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
    if latest_live_recommendation(session_key) is None:
        return {"ok": True, "live_plan": None, "action": "already_clear"}
    if live_price is None:
        from mokli.trading.market_context import resolve_live_quote

        quote, _source = resolve_live_quote(DATA_SYMBOL)
        live_price = quote.mid if quote is not None else None
    live = sync_session_live_plan(session_key, live_price=live_price, price_known=True)
    if live:
        graded = grade_outcome_status(live, live_price=live_price, price_known=True)
        if force_close_invalidated and graded in CLOSED_OUTCOME_STATUSES:
            result = close_plan_for_session(
                session_key,
                status=graded,
                reason=f"auto_close_{graded}",
                category=classify_archive_category(graded),
                live_price=live_price,
                price_known=True,
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
