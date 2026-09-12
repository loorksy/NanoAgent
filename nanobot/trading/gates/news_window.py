"""G1 news window evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nanobot.trading.types import EconomicEvent

BLACKOUT_BEFORE_MS = 30 * 60 * 1000
BLACKOUT_AFTER_MS = 15 * 60 * 1000


@dataclass
class NewsWindowVerdict:
    blocked: bool
    event: EconomicEvent | None = None
    minutes_until_clear: int | None = None


def _parse_event_time(event: EconomicEvent) -> int | None:
    try:
        raw = event.time
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return int(datetime.fromisoformat(raw).timestamp() * 1000)
    except ValueError:
        return None


def evaluate_news_window(events: list[EconomicEvent], now_ms: int) -> NewsWindowVerdict:
    for event in events:
        if event.impact != "high":
            continue
        t = _parse_event_time(event)
        if t is None:
            continue
        start = t - BLACKOUT_BEFORE_MS
        end = t + BLACKOUT_AFTER_MS
        if start <= now_ms <= end:
            mins = max(0, int((end - now_ms) / 60000))
            return NewsWindowVerdict(blocked=True, event=event, minutes_until_clear=mins)
    return NewsWindowVerdict(blocked=False)
