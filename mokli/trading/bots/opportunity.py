"""Multi-setup opportunity scan and event/tradability checks (R16, R17)."""

from __future__ import annotations

from datetime import datetime


def scan_opportunities(*, price: float | None, atr: float, compressed: bool) -> list[str]:
    if price is None or atr <= 0 or compressed:
        return []
    return ["atr_breakout", "range_expansion"]


def tradability(*, spread_points: float, max_spread: float, news_risk: str) -> dict[str, object]:
    blocked = spread_points > max_spread or news_risk == "high"
    return {
        "tradable": not blocked,
        "notice_key": "tradability.blocked" if blocked else "tradability.clear",
    }


def imminent_events(
    events: list[dict[str, object]],
    *,
    now: datetime,
    within_minutes: int,
) -> list[dict[str, object]]:
    horizon = within_minutes * 60
    soon: list[dict[str, object]] = []
    for event in events:
        raw = event.get("at")
        if not isinstance(raw, datetime):
            continue
        delta = (raw - now).total_seconds()
        if 0 <= delta <= horizon:
            soon.append({"title": str(event.get("title") or ""), "notice_key": "calendar.soon"})
    return soon
