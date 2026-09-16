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
            f"Already {open_n} open gold positions (max {max_open})",
            open_positions=open_n,
            max_open=max_open,
        )
    if risk is not None:
        if plan.direction == "buy" and risk.open_buy_losing:
            return veto(
                "A losing gold buy is already open — no doubling the same side",
                open_buy_losing=True,
            )
        if plan.direction == "sell" and risk.open_sell_losing:
            return veto(
                "A losing gold sell is already open — no doubling the same side",
                open_sell_losing=True,
            )
    return passed(open_positions=open_n, max_open=max_open)


def evaluate_no_martingale(*, adding_to_loser: bool) -> GateCheck:
    if adding_to_loser:
        return veto("Martingale / add-to-loser is blocked under volatility")
    return passed()
