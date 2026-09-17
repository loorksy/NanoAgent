"""HITL proposal expiry and confirm-time slippage (execution bracket, not rule 182)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.policy import GOLD_POINT, live


def evaluate_proposal_ttl(*, created_ms: int, now_ms: int) -> GateCheck:
    p = live()
    age_s = (now_ms - created_ms) / 1000
    if age_s > p.PROPOSAL_TTL_SECONDS:
        return veto(
            "gate.proposal.expired",
            age_seconds=age_s,
            limit=p.PROPOSAL_TTL_SECONDS,
        )
    return passed(age_seconds=age_s)


def evaluate_confirm_slippage(*, proposed_price: float, live_price: float) -> GateCheck:
    p = live()
    points = abs(live_price - proposed_price) / GOLD_POINT
    if points > p.MAX_CONFIRM_SLIPPAGE_POINTS:
        return veto(
            "gate.proposal.slippage",
            slip_points=points,
            limit=p.MAX_CONFIRM_SLIPPAGE_POINTS,
        )
    return passed(slip_points=points)
