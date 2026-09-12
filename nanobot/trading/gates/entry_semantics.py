"""G6 entry coherence validation."""

from __future__ import annotations

from nanobot.trading.types import EntryPlan

DEFAULT_MAX_ATR_DISTANCE = 0.3
MAX_TARGET_ATR_DISTANCE = 25


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
        dist = abs(target - plan.entry) / max(atr, 0.01)
        if dist > MAX_TARGET_ATR_DISTANCE:
            reasons.append(f"Target {target} exceeds {MAX_TARGET_ATR_DISTANCE} ATR")
    return len(reasons) == 0, reasons
