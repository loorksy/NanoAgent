"""Deterministic trade-management helpers (4.2–4.4, playbook 38/39/137/153)."""

from __future__ import annotations

from nanobot.trading.policy import GOLD_POINT, live
from nanobot.trading.types import EntryPlan


def should_move_to_breakeven(plan: EntryPlan, live_px: float) -> bool:
    p = live()
    risk = abs(plan.entry - plan.stop_loss)
    if risk <= 0:
        return False
    favorable = abs(live_px - plan.entry)
    if plan.direction == "buy" and live_px <= plan.entry:
        return False
    if plan.direction == "sell" and live_px >= plan.entry:
        return False
    return favorable >= risk * p.BREAKEVEN_RR


def trailing_stop(plan: EntryPlan, live_px: float, atr: float) -> float:
    p = live()
    trail = atr * p.TRAIL_ATR_MULT
    if plan.direction == "buy":
        candidate = live_px - trail
        return max(plan.stop_loss, candidate)
    candidate = live_px + trail
    return min(plan.stop_loss, candidate) if plan.stop_loss else candidate


def partial_close_fraction(plan: EntryPlan, live_px: float) -> float:
    p = live()
    if not plan.targets:
        return 0.0
    t1 = plan.targets[0]
    hit_t1 = (plan.direction == "buy" and live_px >= t1) or (plan.direction == "sell" and live_px <= t1)
    if not hit_t1:
        return 0.0
    if len(plan.targets) > 1:
        t2 = plan.targets[1]
        hit_t2 = (plan.direction == "buy" and live_px >= t2) or (plan.direction == "sell" and live_px <= t2)
        if hit_t2:
            return p.PARTIAL_TP1_FRACTION + p.PARTIAL_TP2_FRACTION
    return p.PARTIAL_TP1_FRACTION


def staged_close_fraction(plan: EntryPlan, live_px: float) -> float:
    """Playbook 153 — 40 / 30 / 30 across three targets."""
    p = live()
    closed = 0.0
    for i, target in enumerate(plan.targets[:3]):
        hit = (plan.direction == "buy" and live_px >= target) or (
            plan.direction == "sell" and live_px <= target
        )
        if hit:
            closed += p.PARTIAL_TP_SPLIT[i]
    return min(1.0, closed)


def profit_lock_stop(plan: EntryPlan, live_px: float) -> float | None:
    p = live()
    if not plan.targets:
        return None
    farthest = plan.targets[-1]
    run = abs(farthest - plan.entry)
    moved = abs(live_px - plan.entry)
    favorable = (plan.direction == "buy" and live_px > plan.entry) or (
        plan.direction == "sell" and live_px < plan.entry
    )
    if not favorable or run <= 0 or moved < run * p.PROFIT_LOCK_AT_TARGET_FRACTION:
        return None
    lock = plan.entry + (farthest - plan.entry) * p.PROFIT_LOCK_KEEP_FRACTION
    return lock


def overnight_stop(plan: EntryPlan) -> float:
    p = live()
    buf = p.OVERNIGHT_SL_BUFFER_POINTS * GOLD_POINT
    if plan.direction == "buy":
        return plan.stop_loss - buf
    return plan.stop_loss + buf
