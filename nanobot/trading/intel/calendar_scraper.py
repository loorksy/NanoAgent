"""FEATURE-04 — free economic calendar scraper (Forex Factory JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.request import urlopen

from nanobot.trading.news.forex_factory import fetch_upcoming_events

_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

IMPACT_MAP = {"red": "high", "orange": "medium", "yellow": "low", "high": "high", "medium": "medium"}


@dataclass(frozen=True)
class CalendarRow:
    title: str
    time: str
    currency: str
    impact: str
    forecast: str = ""
    previous: str = ""
    actual: str | None = None
    surprise: float | None = None


def _surprise(actual: str | None, forecast: str) -> float | None:
    if not actual or not forecast:
        return None
    try:
        a = float(str(actual).replace("%", "").replace(",", "").strip())
        f = float(str(forecast).replace("%", "").replace(",", "").strip())
        return a - f
    except ValueError:
        return None


def _row_from_mapping(row: dict[str, Any]) -> CalendarRow:
    actual = row.get("actual")
    forecast = str(row.get("forecast") or row.get("consensus") or "")
    impact = IMPACT_MAP.get(str(row.get("impact", "medium")).lower(), "medium")
    return CalendarRow(
        title=str(row.get("title") or row.get("event") or ""),
        time=str(row.get("time") or row.get("date") or row.get("datetime") or ""),
        currency=str(row.get("currency") or row.get("country") or ""),
        impact=impact,
        forecast=forecast,
        previous=str(row.get("previous") or ""),
        actual=None if actual is None else str(actual),
        surprise=_surprise(None if actual is None else str(actual), forecast),
    )


def parse_calendar_json(payload: Any) -> list[CalendarRow]:
    rows: list[CalendarRow] = []
    if isinstance(payload, dict):
        items = payload.get("events") or payload.get("data") or []
    else:
        items = payload
    if not isinstance(items, list):
        return rows
    for item in items:
        if isinstance(item, dict):
            rows.append(_row_from_mapping(item))
    return rows


def fetch_calendar_json_sync(*, timeout: float = 8.0) -> list[CalendarRow]:
    try:
        with urlopen(_CALENDAR_URL, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return parse_calendar_json(raw)


async def fetch_economic_calendar(*, now: datetime | None = None) -> list[CalendarRow]:
    del now  # signature reserved for daily 00:01 GMT refresh callers
    existing = fetch_upcoming_events(limit=40)
    if existing:
        return parse_calendar_json(existing)
    return fetch_calendar_json_sync()
