"""G12 — daily drawdown breaker, equity spike, kill switch (3.2, 191, news 61, 7.1)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_drawdown_breaker(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is not None and risk.kill_switch:
        return veto("Kill switch is engaged — all new risk is blocked", kill_switch=True)
    if risk is not None and risk.emergency_lock:
        return veto("Emergency news lock is engaged", emergency_lock=True)
    dd = 0.0 if risk is None else float(risk.daily_drawdown_pct or 0.0)
    if dd >= p.DAILY_DRAWDOWN_PCT:
        return veto(
            f"Daily drawdown {dd:.2%} reached the {p.DAILY_DRAWDOWN_PCT:.0%} breaker",
            daily_drawdown_pct=dd,
            limit=p.DAILY_DRAWDOWN_PCT,
        )
    spike = 0.0 if risk is None else float(risk.equity_spike_pct or 0.0)
    if spike >= p.EQUITY_SPIKE_PCT:
        return veto(
            f"Floating equity dropped {spike:.2%} in one candle (limit {p.EQUITY_SPIKE_PCT:.0%})",
            equity_spike_pct=spike,
            limit=p.EQUITY_SPIKE_PCT,
        )
    return passed(daily_drawdown_pct=dd)
