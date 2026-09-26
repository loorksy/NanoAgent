"""G11 — max concurrent gold positions and no doubling a losing side (3.5, 184, news 58)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan


def evaluate_max_positions(
    plan: EntryPlan,
    risk: RiskSnapshot | None,
    *,
    max_open: int | None = None,
) -> GateCheck:
    p = live()
    if max_open is None:
        max_open = p.MAX_OPEN_GOLD_POSITIONS
    open_n = 0 if risk is None else int(risk.open_positions)
    if max_open > 0 and open_n >= max_open:
        return veto(
            "gate.positions.cap",
            open_positions=open_n,
            max_open=max_open,
        )
    if risk is not None:
        if plan.direction == "buy" and risk.open_buy_losing:
            return veto(
                "gate.positions.losing_buy",
                open_buy_losing=True,
            )
        if plan.direction == "sell" and risk.open_sell_losing:
            return veto(
                "gate.positions.losing_sell",
                open_sell_losing=True,
            )
    return passed(open_positions=open_n, max_open=max_open)


def evaluate_max_total_lots(risk: RiskSnapshot | None) -> GateCheck:
    """T-3.5 — cap aggregate gold lots, not only the position count. 0 disables the cap."""
    cap = live().MAX_TOTAL_LOTS
    open_lots = 0.0 if risk is None else float(risk.open_lots)
    requested = 0.0 if risk is None or risk.proposed_lot is None else float(risk.proposed_lot)
    if cap <= 0:
        return passed(open_lots=open_lots, max_total_lots=cap)
    if open_lots + requested > cap + 1e-9:
        return veto(
            "gate.positions.total_lots",
            open_lots=open_lots,
            requested_lot=requested,
            max_total_lots=cap,
        )
    return passed(open_lots=open_lots, requested_lot=requested, max_total_lots=cap)


def evaluate_no_martingale(*, adding_to_loser: bool) -> GateCheck:
    if adding_to_loser:
        return veto("gate.positions.martingale")
    return passed()
