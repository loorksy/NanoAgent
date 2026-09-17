"""G12 — daily drawdown breaker, equity spike, kill switch (3.2, 191, news 61, 7.1)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_drawdown_breaker(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is not None and risk.kill_switch:
        return veto("gate.drawdown.kill_switch", kill_switch=True)
    if risk is not None and risk.emergency_lock:
        return veto("gate.drawdown.emergency_lock", emergency_lock=True)
    dd = 0.0 if risk is None else float(risk.daily_drawdown_pct or 0.0)
    if dd >= p.DAILY_DRAWDOWN_PCT:
        return veto(
            "gate.drawdown.daily",
            daily_drawdown_pct=dd * 100,
            limit=p.DAILY_DRAWDOWN_PCT * 100,
        )
    spike = 0.0 if risk is None else float(risk.equity_spike_pct or 0.0)
    if spike >= p.EQUITY_SPIKE_PCT:
        return veto(
            "gate.drawdown.equity_spike",
            equity_spike_pct=spike * 100,
            limit=p.EQUITY_SPIKE_PCT * 100,
        )
    return passed(daily_drawdown_pct=dd)


def flatten_required_reason(risk: RiskSnapshot | None) -> str | None:
    """S3.2 / S7.1 — when flatten is required. Execution itself stays HITL."""
    p = live()
    if risk is None:
        return None
    if risk.kill_switch:
        return "kill_switch"
    if risk.emergency_lock:
        return "emergency_lock"
    if float(risk.daily_drawdown_pct or 0.0) >= p.DAILY_DRAWDOWN_PCT:
        return "daily_drawdown"
    return None
