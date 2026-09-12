"""Tradability assessment before persisting recommendations."""

from __future__ import annotations

from nanobot.trading.types import FinalDecisionResult


def assess_plan_tradability(decision: FinalDecisionResult) -> tuple[bool, str]:
    """Return whether a plan should be stored and a short reason."""
    if decision.decision == "wait":
        return False, "wait decision"
    if decision.gate_chain and not decision.gate_chain.allowed:
        return False, "gates vetoed"
    rec = decision.recommendation
    if rec.action not in ("buy", "sell"):
        return False, "no actionable side"
    if not rec.entry or not rec.stop_loss or not rec.targets:
        return False, "incomplete levels"
    if rec.entry <= 0 or rec.stop_loss <= 0:
        return False, "invalid prices"
    return True, "tradable"
