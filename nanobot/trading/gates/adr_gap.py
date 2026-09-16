"""ADR over-extension and gap-chase blocks (news 82 / 90)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.policy import GOLD_POINT, live


def evaluate_adr_chase(*, session_range: float, adr: float) -> GateCheck:
    p = live()
    if adr <= 0:
        return passed()
    if session_range >= adr * p.ADR_CHASE_PCT:
        return veto(
            f"Session range {session_range:.2f} is {session_range / adr:.0%} of ADR — no chase",
            session_range=session_range,
            adr=adr,
        )
    return passed(session_range=session_range, adr=adr)


def evaluate_gap_chase(*, gap_points: float) -> GateCheck:
    p = live()
    if gap_points >= p.GAP_NO_CHASE_POINTS:
        return veto(
            f"Opening gap {gap_points:.0f} points exceeds {p.GAP_NO_CHASE_POINTS:.0f} — do not chase",
            gap_points=gap_points,
        )
    return passed(gap_points=gap_points)


def gap_points(open_price: float, prior_close: float) -> float:
    return abs(open_price - prior_close) / GOLD_POINT
