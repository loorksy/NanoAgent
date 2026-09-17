"""Entry coherence validation."""

from __future__ import annotations

from nanobot.trading.i18n import tr
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan


def validate_entry_coherence(plan: EntryPlan, atr: float) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if plan.entry <= 0 or plan.stop_loss <= 0 or not plan.targets:
        reasons.append(tr("gate.entry.missing_levels"))
        return False, reasons
    if plan.direction == "buy" and plan.stop_loss >= plan.entry:
        reasons.append(tr("gate.entry.buy_stop"))
    if plan.direction == "sell" and plan.stop_loss <= plan.entry:
        reasons.append(tr("gate.entry.sell_stop"))
    for target in plan.targets:
        limit = live().TARGET_MAX_ATR_DISTANCE
        dist = abs(target - plan.entry) / max(atr, 0.01)
        if dist > limit:
            reasons.append(tr("gate.entry.target_atr", target=target, limit=limit))
    return len(reasons) == 0, reasons
