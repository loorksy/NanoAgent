"""Live plan revalidation (live-price confirmation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanobot.trading.i18n import tr
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan

RevalidationStatus = Literal["ok", "reanchored", "invalidated", "targets_passed", "unavailable"]


@dataclass
class RevalidationResult:
    status: RevalidationStatus
    reason: str = ""
    reason_key: str = ""
    reanchored_entry: float | None = None


def revalidate_plan(plan: EntryPlan, live_price: float | None, atr: float) -> RevalidationResult:
    if live_price is None or live_price <= 0:
        return RevalidationResult(
            status="unavailable",
            reason_key="gate.revalidate.no_quote",
            reason=tr("gate.revalidate.no_quote"),
        )

    slip = (atr or 1.0) * live().G7_MAX_SLIPPAGE_ATR
    if plan.direction == "buy":
        if live_price <= plan.stop_loss:
            return RevalidationResult(
                status="invalidated",
                reason_key="gate.revalidate.below_stop",
                reason=tr("gate.revalidate.below_stop"),
            )
        if plan.targets and live_price >= max(plan.targets):
            return RevalidationResult(
                status="targets_passed",
                reason_key="gate.revalidate.targets_passed",
                reason=tr("gate.revalidate.targets_passed"),
            )
        if abs(live_price - plan.entry) > slip:
            return RevalidationResult(
                status="reanchored",
                reason_key="gate.revalidate.reanchored",
                reason=tr("gate.revalidate.reanchored"),
                reanchored_entry=live_price,
            )
    else:
        if live_price >= plan.stop_loss:
            return RevalidationResult(
                status="invalidated",
                reason_key="gate.revalidate.above_stop",
                reason=tr("gate.revalidate.above_stop"),
            )
        if plan.targets and live_price <= min(plan.targets):
            return RevalidationResult(
                status="targets_passed",
                reason_key="gate.revalidate.targets_passed",
                reason=tr("gate.revalidate.targets_passed"),
            )
        if abs(live_price - plan.entry) > slip:
            return RevalidationResult(
                status="reanchored",
                reason_key="gate.revalidate.reanchored",
                reason=tr("gate.revalidate.reanchored"),
                reanchored_entry=live_price,
            )
    return RevalidationResult(status="ok")
