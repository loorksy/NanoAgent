"""Weekend open plan (R7). Entries stay off until the Monday London session."""

from __future__ import annotations

from datetime import datetime


def closed_market_plan(
    *,
    now: datetime,
    last_close: float,
    friday_close: float,
    atr: float,
) -> dict[str, object]:
    weekend = now.weekday() >= 5
    gap = last_close - friday_close
    return {
        "closed": weekend,
        "entries_allowed": not weekend,
        "gap": gap,
        "atr": atr,
        "wait_for": "london" if weekend else "",
        "notice_key": "closed_market.weekend" if weekend else "",
    }
