"""G1 news window evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nanobot.trading.policy import live
from nanobot.trading.types import EconomicEvent

# Stricter than news-encyclopedia rule 1 (15m pre-news): keep 30m / 15m.
BLACKOUT_BEFORE_MS = 30 * 60 * 1000
BLACKOUT_AFTER_MS = 15 * 60 * 1000


def _blackout_ms() -> tuple[int, int]:
    p = live()
    return (
        int(p.NEWS_BLACKOUT_BEFORE_MINUTES * 60 * 1000),
        int(p.NEWS_BLACKOUT_AFTER_MINUTES * 60 * 1000),
    )


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


def nearest_high_impact(events: list[EconomicEvent], now_ms: int) -> tuple[float | None, float | None]:
    """Return (minutes_until, minutes_since) the nearest high-impact event."""
    soonest_to: float | None = None
    soonest_since: float | None = None
    for event in events:
        if event.impact != "high":
            continue
        t = _parse_event_time(event)
        if t is None:
            continue
        if t >= now_ms:
            mins = (t - now_ms) / 60000
            soonest_to = mins if soonest_to is None else min(soonest_to, mins)
        else:
            mins = (now_ms - t) / 60000
            soonest_since = mins if soonest_since is None else min(soonest_since, mins)
    return soonest_to, soonest_since


def evaluate_news_window(events: list[EconomicEvent], now_ms: int) -> NewsWindowVerdict:
    for event in events:
        if event.impact != "high":
            continue
        t = _parse_event_time(event)
        if t is None:
            continue
        before_ms, after_ms = _blackout_ms()
        start = t - before_ms
        end = t + after_ms
        if start <= now_ms <= end:
            mins = max(0, int((end - now_ms) / 60000))
            return NewsWindowVerdict(blocked=True, event=event, minutes_until_clear=mins)
    return NewsWindowVerdict(blocked=False)
