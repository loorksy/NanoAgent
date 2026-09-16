"""G6 entry coherence validation."""

from __future__ import annotations

from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan


def validate_entry_coherence(plan: EntryPlan, atr: float) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if plan.entry <= 0 or plan.stop_loss <= 0 or not plan.targets:
        reasons.append("Missing entry, stop, or targets")
        return False, reasons
    if plan.direction == "buy" and plan.stop_loss >= plan.entry:
        reasons.append("Buy stop must be below entry")
    if plan.direction == "sell" and plan.stop_loss <= plan.entry:
        reasons.append("Sell stop must be above entry")
    for target in plan.targets:
        limit = live().TARGET_MAX_ATR_DISTANCE
        dist = abs(target - plan.entry) / max(atr, 0.01)
        if dist > limit:
            reasons.append(f"Target {target} exceeds {limit} ATR")
    return len(reasons) == 0, reasons
