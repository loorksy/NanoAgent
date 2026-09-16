"""G16 — bad-tick filter (section 7.4, news 66)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import GOLD_POINT, live


def evaluate_bad_tick(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.last_mid is None or risk.current_mid is None:
        return unavailable("Tick pair unavailable")
    jump = abs(risk.current_mid - risk.last_mid) / GOLD_POINT
    if jump >= p.BAD_TICK_POINTS:
        return veto(
            f"Bad tick: {jump:.0f}-point spike vs prior tick (limit {p.BAD_TICK_POINTS:.0f})",
            jump_points=jump,
            limit=p.BAD_TICK_POINTS,
        )
    return passed(jump_points=jump)
