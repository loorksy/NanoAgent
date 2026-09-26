"""Calendar rows for the operator log (R13). Network fetch stays optional."""

from __future__ import annotations

from typing import cast


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
