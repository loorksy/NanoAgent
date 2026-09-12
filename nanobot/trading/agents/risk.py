"""Risk agent — trade candidates from structure + ATR."""

from __future__ import annotations

from nanobot.trading.types import (
    AgentMarketContext,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    TradeCandidate,
    TradeValidationResult,
)


def _rr(entry: float, stop: float, target: float, action: str) -> float:
    risk = abs(entry - stop)
    reward = abs(target - entry) if action == "buy" else abs(entry - target)
    return reward / risk if risk > 0 else 0.0


def run_risk_agent(
    market: AgentMarketContext,
    structure: StructureResult,
    supply_demand: SupplyDemandResult,
) -> RiskAgentResult:
    atr = market.atr or 1.0
    price = market.last_close
    candidates: list[TradeCandidate] = []

    if structure.trend == "uptrend" or (
        structure.latest_structure_event and structure.latest_structure_event.direction == "bullish"
    ):
        stop = price - atr * 1.5
        t1 = price + atr * 2
        t2 = price + atr * 4
        candidates.append(
            TradeCandidate(
                id="cand-bull-1",
                action="buy",
                entry=price,
                entry_type="market",
                stop_loss=stop,
                targets=[t1, t2],
                rr=_rr(price, stop, t2, "buy"),
                quality_score=0.65,
                setup_type="structure_break",
            )
        )
    if structure.trend == "downtrend" or (
        structure.latest_structure_event and structure.latest_structure_event.direction == "bearish"
    ):
        stop = price + atr * 1.5
        t1 = price - atr * 2
        t2 = price - atr * 4
        candidates.append(
            TradeCandidate(
                id="cand-bear-1",
                action="sell",
                entry=price,
                entry_type="market",
                stop_loss=stop,
                targets=[t1, t2],
                rr=_rr(price, stop, t2, "sell"),
                quality_score=0.65,
                setup_type="structure_break",
            )
        )

    if supply_demand.nearest_demand and not candidates:
        z = supply_demand.nearest_demand
        entry = (z.low + z.high) / 2
        stop = z.low - atr * 0.5
        t1 = entry + atr * 2
        candidates.append(
            TradeCandidate(
                id="cand-demand-1",
                action="buy",
                entry=entry,
                entry_type="limit",
                stop_loss=stop,
                targets=[t1],
                rr=_rr(entry, stop, t1, "buy"),
                quality_score=0.55,
                setup_type="demand_zone",
            )
        )

    selected = max(candidates, key=lambda c: c.quality_score) if candidates else None
    if selected is None:
        wait = TradeCandidate(
            id="cand-wait",
            action="wait",
            entry=price,
            entry_type="none",
            stop_loss=price,
            targets=[],
            rr=0.0,
            quality_score=0.0,
        )
        return RiskAgentResult(
            proposed_trade=wait,
            validation=TradeValidationResult(accepted=False, reasons=["No setup"]),
            selected_candidate=None,
            candidates=[],
        )

    validation = TradeValidationResult(
        accepted=selected.rr >= 1.5,
        reasons=[] if selected.rr >= 1.5 else ["R:R below minimum"],
        warnings=[],
        rr=selected.rr,
    )
    return RiskAgentResult(
        proposed_trade=selected,
        validation=validation,
        selected_candidate=selected,
        candidates=candidates,
    )
