"""G20 — position sizing from balance risk percent (3.1, 47, 188, 199, news 16 / 67)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import GOLD_POINT, USD_PER_POINT_PER_LOT, live
from nanobot.trading.types import EntryPlan


def risk_percent(risk: RiskSnapshot | None) -> float:
    p = live()
    pct = p.RISK_PCT_NEWS_DAY if (risk and risk.news_day) else p.RISK_PCT_DEFAULT
    if risk and risk.atr is not None and risk.atr_baseline:
        if risk.atr_baseline > 0 and risk.atr >= risk.atr_baseline * p.ATR_DOUBLE_LOT_HALVE:
            pct = min(pct, p.RISK_PCT_DEFAULT / 2.0)
    return min(pct, p.RISK_PCT_MAX)


def lot_from_balance(
    balance: float,
    entry: float,
    stop: float,
    *,
    risk_pct: float | None = None,
) -> float:
    p = live()
    if risk_pct is None:
        risk_pct = p.RISK_PCT_DEFAULT
    stop_points = abs(entry - stop) / GOLD_POINT
    if stop_points <= 0 or balance <= 0:
        return 0.0
    risk_amount = balance * min(risk_pct, p.RISK_PCT_MAX)
    return risk_amount / (stop_points * USD_PER_POINT_PER_LOT)


def evaluate_position_sizing(plan: EntryPlan, risk: RiskSnapshot | None) -> GateCheck:
    if risk is None or risk.account_balance is None:
        return unavailable("Account balance unavailable for lot sizing")
    # Playbook 199: size from balance, never floating equity.
    balance = float(risk.account_balance)
    pct = risk_percent(risk)
    expected = lot_from_balance(balance, plan.entry, plan.stop_loss, risk_pct=pct)
    proposed = risk.proposed_lot
    p = live()
    evidence = {
        "balance": balance,
        "risk_pct": pct,
        "expected_lot": expected,
        "sized_from": "balance",
    }
    if proposed is None:
        return passed(**evidence)
    # Playbook 188: dual check — reject decimal disasters (>2x or <0.5x expected).
    if expected <= 0:
        return veto("Computed lot is zero — stop distance or balance invalid", **evidence)
    ratio = proposed / expected
    if ratio > p.LOT_DUAL_CHECK_HIGH or ratio < p.LOT_DUAL_CHECK_LOW:
        return veto(
            f"Proposed lot {proposed} fails dual-check against sized lot {expected:.4f}",
            proposed_lot=proposed,
            **evidence,
        )
    return passed(proposed_lot=proposed, **evidence)
