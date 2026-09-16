"""Shared inputs for G8+ risk / execution gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskSnapshot:
    """Optional live account / quote facts. Missing fields skip the dependent gate."""

    spread_points: float | None = None
    normal_spread_points: float | None = None
    quote_age_seconds: float | None = None
    bid: float | None = None
    ask: float | None = None
    last_mid: float | None = None
    current_mid: float | None = None
    open_positions: int = 0
    open_buy_losing: bool = False
    open_sell_losing: bool = False
    daily_drawdown_pct: float = 0.0
    equity_spike_pct: float = 0.0
    consecutive_losses: int = 0
    cooldown_until_ms: int = 0
    cooldown_reason: str = ""
    margin_level_pct: float | None = None
    ping_ms: float | None = None
    exec_latency_ms: float | None = None
    expected_slippage_points: float | None = None
    proposed_lot: float | None = None
    account_balance: float | None = None
    account_equity: float | None = None
    kill_switch: bool = False
    emergency_lock: bool = False
    holiday: bool = False
    news_day: bool = False
    atr: float | None = None
    atr_baseline: float | None = None
    adr: float | None = None
    session_range: float | None = None
    pending_created_ms: int | None = None
    minutes_to_high_impact: float | None = None
    minutes_since_high_impact: float | None = None
    seconds_since_high_impact: float | None = None
    spread_stable_seconds: float | None = None
    feature_toggles: dict[str, bool] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def toggle(self, name: str, default: bool = True) -> bool:
        if name not in self.feature_toggles:
            return default
        return bool(self.feature_toggles[name])
