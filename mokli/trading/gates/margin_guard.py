"""G18 — free-margin / margin-level guard (news 70)."""

from __future__ import annotations

from mokli.trading.gates.check import GateCheck, passed, unavailable, veto
from mokli.trading.gates.risk_snapshot import RiskSnapshot
from mokli.trading.policy import live


def evaluate_margin_guard(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.margin_level_pct is None:
        return unavailable("gate.margin.unavailable")
    level = float(risk.margin_level_pct)
    if level < p.MARGIN_MIN_PCT:
        return veto(
            "gate.margin.low",
            margin_level_pct=level,
            limit=p.MARGIN_MIN_PCT,
        )
    return passed(margin_level_pct=level)
