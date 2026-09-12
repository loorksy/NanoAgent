"""News & macro agent — lightweight calendar stub."""

from __future__ import annotations

import os

from nanobot.trading.types import NewsMacroResult


def news_provider_configured() -> bool:
    # Stub calendar is always available until a live provider is wired (Phase 5).
    if os.environ.get("FOREX_FACTORY_ENABLED", "").strip() in {"1", "true", "yes"}:
        return True
    return os.environ.get("TRADING_NEWS_STUB", "1").strip() not in {"0", "false", "no"}


def run_news_macro_agent() -> NewsMacroResult:
    return NewsMacroResult(
        news_risk="low",
        bias_impact="mixed",
        affected_currencies=["USD", "XAU"],
        upcoming_events=[],
        trade_allowed=True,
        reason="No high-impact events in window (stub calendar)",
    )
