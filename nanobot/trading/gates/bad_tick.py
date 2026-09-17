"""G16 — bad-tick filter (section 7.4, news 66)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import GOLD_POINT, live


def evaluate_bad_tick(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.last_mid is None or risk.current_mid is None:
        return unavailable("gate.tick.pair_unavailable")
    jump = abs(risk.current_mid - risk.last_mid) / GOLD_POINT
    if jump >= p.BAD_TICK_POINTS:
        return veto(
            "gate.tick.spike",
            jump_points=jump,
            limit=p.BAD_TICK_POINTS,
        )
    return passed(jump_points=jump)
