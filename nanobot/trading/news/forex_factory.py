"""Lightweight Forex Factory calendar feed for gold macro agent."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_GOLD_CURRENCIES = frozenset({"USD", "XAU", "ALL"})


def fetch_upcoming_events(limit: int = 12) -> list[dict[str, Any]]:
    """Return upcoming high/medium impact events relevant to gold."""
    if os.environ.get("FOREX_FACTORY_ENABLED", "").strip() not in {"1", "true", "yes"}:
        return []
    try:
        with urllib.request.urlopen(_CALENDAR_URL, timeout=8) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    events: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return events

    for row in raw:
        if not isinstance(row, dict):
            continue
        currency = str(row.get("country", row.get("currency", ""))).upper()
        if currency not in _GOLD_CURRENCIES and "USD" not in currency:
            continue
        impact = str(row.get("impact", "")).lower()
        if impact not in {"high", "medium", "red", "orange"}:
            continue
        events.append(
            {
                "title": str(row.get("title", row.get("event", ""))),
                "currency": currency,
                "impact": impact,
                "time": row.get("date", row.get("time", "")),
            }
        )
        if len(events) >= limit:
            break
    return events
