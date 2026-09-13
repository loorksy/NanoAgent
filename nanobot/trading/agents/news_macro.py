"""News & macro agent — live Forex Factory calendar or explicit unavailable."""

from __future__ import annotations

import os

from nanobot.trading.news.forex_factory import fetch_upcoming_events
from nanobot.trading.types import EconomicEvent, NewsMacroResult


def news_provider_configured() -> bool:
    return os.environ.get("FOREX_FACTORY_ENABLED", "").strip() in {"1", "true", "yes"}


def _wire_events(events: list[dict]) -> list[EconomicEvent]:
    wired: list[EconomicEvent] = []
    for row in events:
        impact = str(row.get("impact", "")).lower()
        if impact in {"red", "high"}:
            level = "high"
        elif impact in {"orange", "medium"}:
            level = "medium"
        else:
            level = "low"
        wired.append(
            EconomicEvent(
                title=str(row.get("title", row.get("event", ""))),
                time=str(row.get("time", row.get("date", ""))),
                impact=level,
                currency=str(row.get("currency", row.get("country", ""))) or None,
            )
        )
    return wired


def run_news_macro_agent() -> NewsMacroResult:
    if not news_provider_configured():
        return NewsMacroResult(
            news_risk="unknown",
            bias_impact="unknown",
            affected_currencies=["USD", "XAU"],
            upcoming_events=[],
            trade_allowed=False,
            reason="Macro calendar not configured (set FOREX_FACTORY_ENABLED=1)",
        )

    events = fetch_upcoming_events()
    if not events:
        return NewsMacroResult(
            news_risk="low",
            bias_impact="mixed",
            affected_currencies=["USD", "XAU"],
            upcoming_events=[],
            trade_allowed=True,
            reason="No high-impact events in calendar window",
        )

    wired = _wire_events(events)
    high_impact = [event for event in wired if event.impact == "high"]
    news_risk = "high" if high_impact else "medium"
    return NewsMacroResult(
        news_risk=news_risk,
        bias_impact="mixed",
        affected_currencies=["USD", "XAU"],
        upcoming_events=wired,
        trade_allowed=len(high_impact) == 0,
        reason=f"{len(events)} upcoming macro events (Forex Factory)",
    )
