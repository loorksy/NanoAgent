"""News & macro agent — stub or Forex Factory calendar."""

from __future__ import annotations

import os

from nanobot.trading.news.forex_factory import fetch_upcoming_events
from nanobot.trading.types import NewsMacroResult


def news_provider_configured() -> bool:
    if os.environ.get("FOREX_FACTORY_ENABLED", "").strip() in {"1", "true", "yes"}:
        return True
    return os.environ.get("TRADING_NEWS_STUB", "1").strip() not in {"0", "false", "no"}


def run_news_macro_agent() -> NewsMacroResult:
    live = os.environ.get("FOREX_FACTORY_ENABLED", "").strip() in {"1", "true", "yes"}
    events = fetch_upcoming_events() if live else []
    if events:
        high_impact = [e for e in events if str(e.get("impact", "")).lower() in {"high", "red"}]
        news_risk = "high" if high_impact else "medium"
        return NewsMacroResult(
            news_risk=news_risk,
            bias_impact="mixed",
            affected_currencies=["USD", "XAU"],
            upcoming_events=events,
            trade_allowed=len(high_impact) == 0,
            reason=f"{len(events)} upcoming macro events (Forex Factory)",
        )
    return NewsMacroResult(
        news_risk="low",
        bias_impact="mixed",
        affected_currencies=["USD", "XAU"],
        upcoming_events=[],
        trade_allowed=True,
        reason="No high-impact events in window (stub calendar)",
    )
