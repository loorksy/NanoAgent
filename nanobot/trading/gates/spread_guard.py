"""G9 — spread guard (section 3.3, news 5 / 56)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_spread_guard(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.spread_points is None:
        return unavailable("gate.spread.unavailable")
    spread = risk.spread_points
    if spread > p.SPREAD_MAX_POINTS:
        stable = risk.spread_stable_seconds
        if stable is not None and stable >= p.SPREAD_STABLE_SECONDS:
            return passed(spread_points=spread, recovered=True)
        return veto(
            "gate.spread.wide",
            spread_points=spread,
            max_points=p.SPREAD_MAX_POINTS,
        )
    minutes = risk.minutes_to_high_impact
    normal = risk.normal_spread_points
    if (
        minutes is not None
        and minutes <= p.SPREAD_PRE_NEWS_MINUTES
        and normal is not None
        and normal > 0
        and spread > normal * p.SPREAD_MULTIPLIER_PRE_NEWS
    ):
        return veto(
            "gate.spread.pre_news",
            spread_points=spread,
            multiplier=p.SPREAD_MULTIPLIER_PRE_NEWS,
            normal_spread_points=normal,
        )
    return passed(spread_points=spread)
