"""G7 live plan revalidation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan

RevalidationStatus = Literal["ok", "reanchored", "invalidated", "targets_passed", "unavailable"]


@dataclass
class RevalidationResult:
    status: RevalidationStatus
    reason: str = ""
    reanchored_entry: float | None = None


MAX_SLIPPAGE_ATR = 0.5


def revalidate_plan(plan: EntryPlan, live_price: float | None, atr: float) -> RevalidationResult:
    if live_price is None or live_price <= 0:
        return RevalidationResult(status="unavailable", reason="Live quote unavailable")

    slip = (atr or 1.0) * live().G7_MAX_SLIPPAGE_ATR
    if plan.direction == "buy":
        if live_price <= plan.stop_loss:
            return RevalidationResult(status="invalidated", reason="Price below stop")
        if plan.targets and live_price >= max(plan.targets):
            return RevalidationResult(status="targets_passed", reason="Targets already reached")
        if abs(live_price - plan.entry) > slip:
            return RevalidationResult(
                status="reanchored",
                reason="Reanchored to live price",
                reanchored_entry=live_price,
            )
    else:
        if live_price >= plan.stop_loss:
            return RevalidationResult(status="invalidated", reason="Price above stop")
        if plan.targets and live_price <= min(plan.targets):
            return RevalidationResult(status="targets_passed", reason="Targets already reached")
        if abs(live_price - plan.entry) > slip:
            return RevalidationResult(
                status="reanchored",
                reason="Reanchored to live price",
                reanchored_entry=live_price,
            )
    return RevalidationResult(status="ok")
