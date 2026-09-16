"""G8 — minimum reward-to-risk filter (section 3.6, playbook 196)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan


def reward_risk(entry: float, stop: float, target: float) -> float:
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0
    return abs(target - entry) / risk


def farthest_rr(plan: EntryPlan, *, entry: float | None = None) -> float:
    use_entry = plan.entry if entry is None else entry
    if not plan.targets:
        return 0.0
    return max(reward_risk(use_entry, plan.stop_loss, t) for t in plan.targets)


def evaluate_rr_filter(
    plan: EntryPlan,
    *,
    live_entry: float | None = None,
    min_rr: float | None = None,
    live_min_rr: float | None = None,
) -> GateCheck:
    p = live()
    if min_rr is None:
        min_rr = p.MIN_RR
    if live_min_rr is None:
        live_min_rr = p.MIN_RR_LIVE_FILL
    planned = farthest_rr(plan)
    if planned < min_rr:
        return veto(
            f"Reward-to-risk {planned:.2f} is below the {min_rr:.1f} minimum",
            rr=planned,
            min_rr=min_rr,
        )
    if live_entry is not None:
        live_rr = farthest_rr(plan, entry=live_entry)
        if live_rr < live_min_rr:
            return veto(
                f"Live fill degraded R:R to {live_rr:.2f} (minimum {live_min_rr:.1f})",
                rr=live_rr,
                min_rr=live_min_rr,
                planned_rr=planned,
            )
    return passed(rr=planned, min_rr=min_rr)
