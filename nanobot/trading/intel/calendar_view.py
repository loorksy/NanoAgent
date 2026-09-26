"""Calendar rows for the operator log (R13). Network fetch stays optional."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from nanobot.trading.bots.opportunity import imminent_events


def rows_from_events(events: list[object]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for event in events:
        title = getattr(event, "title", None)
        impact = getattr(event, "impact", None)
        when = getattr(event, "time", None)
        if title is None and isinstance(event, dict):
            mapping = cast(dict[str, object], event)
            title = mapping.get("title")
            impact = mapping.get("impact")
            when = mapping.get("time")
        if not title:
            continue
        rows.append(
            {
                "title": str(title),
                "impact": str(impact or ""),
                "time": str(when or ""),
            }
        )
    return rows


def parse_event_time(value: object) -> datetime | None:
    """Parse an ISO timestamp. ``Z`` is UTC, and a naive value is treated as UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def upcoming_rows(
    rows: Sequence[object],
    *,
    now: datetime,
    within_minutes: int,
) -> list[dict[str, object]]:
    """Turn calendar rows into the imminent-event list the monitor cron reads."""
    prepared: list[dict[str, object]] = []
    for item in rows:
        title = ""
        when: object = None
        if isinstance(item, dict):
            mapping = cast(dict[str, object], item)
            title = str(mapping.get("title") or "")
            when = mapping.get("at", mapping.get("time"))
        else:
            title = str(getattr(item, "title", "") or "")
            when = getattr(item, "time", None)
        parsed = parse_event_time(when)
        if not title or parsed is None:
            continue
        prepared.append({"title": title, "at": parsed})
    return imminent_events(prepared, now=now, within_minutes=within_minutes)
