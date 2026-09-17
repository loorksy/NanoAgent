"""Playbook 36 — time stop after a dead range."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.policy import live


def evaluate_time_stop(*, open_ms: int, now_ms: int, favorable_progress: bool) -> GateCheck:
    p = live()
    age_h = (now_ms - open_ms) / 3_600_000
    if age_h >= p.TIME_STOP_HOURS and not favorable_progress:
        return veto(
            "gate.time_stop.idle",
            age_hours=age_h,
            limit_hours=p.TIME_STOP_HOURS,
        )
    return passed(age_hours=age_h)
