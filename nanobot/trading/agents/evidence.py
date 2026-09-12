"""Frozen evidence JSON for the Lonora synthesizer (modelContext)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from nanobot.trading.types import (
    AgentMarketContext,
    EvidenceSnapshot,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    VisualReview,
)


def _level_prices(*groups: list[Any]) -> list[float]:
    out: list[float] = []
    for group in groups:
        for item in group:
            if item is None:
                continue
            if hasattr(item, "price"):
                out.append(float(item.price))
            elif hasattr(item, "low") and hasattr(item, "high"):
                out.extend([float(item.low), float(item.high)])
            elif isinstance(item, (int, float)):
                out.append(float(item))
    # Stable unique-ish menu rounded to 2dp
    seen: set[float] = set()
    unique: list[float] = []
    for price in out:
        key = round(price, 2)
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique[:40]


def build_evidence_snapshot(
    *,
    market: AgentMarketContext,
    structure: StructureResult,
    liquidity: LiquidityResult,
    supply_demand: SupplyDemandResult,
    mtf: MultiTimeframeResult,
    news: NewsMacroResult,
    risk: RiskAgentResult,
    geometry: dict[str, Any] | None = None,
    visual: VisualReview | None = None,
    team_briefing: str | None = None,
    spread: float | None = None,
) -> EvidenceSnapshot:
    candidates = [
        {
            "id": c.id,
            "action": c.action,
            "entry": c.entry,
            "entryType": c.entry_type,
            "stopLoss": c.stop_loss,
            "targets": list(c.targets),
            "rr": c.rr,
            "qualityScore": c.quality_score,
            "setupType": c.setup_type,
        }
        for c in risk.candidates
        if c.action in ("buy", "sell")
    ]
    evidence_levels = _level_prices(
        structure.support,
        structure.resistance,
        liquidity.equal_highs,
        liquidity.equal_lows,
        [liquidity.nearest_buy_side, liquidity.nearest_sell_side],
        supply_demand.zones,
        [c.entry for c in risk.candidates],
        [c.stop_loss for c in risk.candidates],
        [t for c in risk.candidates for t in c.targets],
    )
    live = market.quote_mid or market.last_close
    if live:
        evidence_levels = _level_prices(evidence_levels, [live])
    payload: dict[str, Any] = {
        "market": {
            "symbol": market.symbol,
            "interval": market.interval,
            "lastClose": market.last_close,
            "live": live,
            "atr": market.atr,
            "spread": spread,
            "sync": asdict(market.sync),
            "candleCount": len(market.candles),
        },
        "structure": {
            "trend": structure.trend,
            "latestEvent": asdict(structure.latest_structure_event)
            if structure.latest_structure_event
            else None,
            "support": [asdict(x) for x in structure.support[:4]],
            "resistance": [asdict(x) for x in structure.resistance[:4]],
        },
        "liquidity": {
            "nearestBuySide": asdict(liquidity.nearest_buy_side)
            if liquidity.nearest_buy_side
            else None,
            "nearestSellSide": asdict(liquidity.nearest_sell_side)
            if liquidity.nearest_sell_side
            else None,
            "latestSweep": asdict(liquidity.latest_sweep) if liquidity.latest_sweep else None,
        },
        "zones": {
            "nearestDemand": asdict(supply_demand.nearest_demand)
            if supply_demand.nearest_demand
            else None,
            "nearestSupply": asdict(supply_demand.nearest_supply)
            if supply_demand.nearest_supply
            else None,
        },
        "mtf": asdict(mtf),
        "geometry": geometry or {},
        "news": {
            "newsRisk": news.news_risk,
            "biasImpact": news.bias_impact,
            "tradeAllowed": news.trade_allowed,
            "reason": news.reason,
            "upcoming": [asdict(e) for e in news.upcoming_events[:6]],
        },
        "candidates": candidates,
        "evidenceLevels": evidence_levels,
        "executionCost": {
            "source": "observed_quote" if spread is not None else "unavailable",
            "observed_spread_pips": spread,
        },
        "visualReview": asdict(visual) if visual else {"state": "not_checked"},
        "statisticalSupport": None,
        "teamBriefing": team_briefing,
    }
    return EvidenceSnapshot(payload=payload, evidence_levels=evidence_levels)
