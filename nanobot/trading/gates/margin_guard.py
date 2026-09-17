"""G18 — free-margin / margin-level guard (news 70)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


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
