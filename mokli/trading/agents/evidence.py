"""Frozen evidence JSON for the decision synthesizer (modelContext)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from mokli.trading.types import (
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


# The decision model reads one JSON document. A character slice of that document
# can end inside a string. The brief is the only field that grows with the team.
_MODEL_EVIDENCE_LIMIT = 18000
_STANCE_LINE = re.compile(r"(?im)^STANCE:\s*(?:buy|sell|wait)\s*$")


def evidence_json_for_model(payload: dict[str, Any], *, limit: int = _MODEL_EVIDENCE_LIMIT) -> str:
    """Serialize frozen evidence for the decision model.

    A short document is unchanged. When a team brief would push it past ``limit``,
    the brief is shortened and the rest of the payload stays. The result still
    parses. The caller's dict is not modified. Other oversized fields are left
    intact rather than cut mid-string.
    """
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    briefing = payload.get("teamBriefing")
    if not isinstance(briefing, str) or not briefing:
        return text
    fitted = _briefing_that_fits(payload, briefing, limit)
    return json.dumps({**payload, "teamBriefing": fitted}, ensure_ascii=False, default=str)


def _briefing_that_fits(payload: dict[str, Any], briefing: str, limit: int) -> str:
    narrative, tail = split_trailing_json(briefing)
    stances = _stance_lines(narrative)
    # Stance lines are appended after the head, so the head search stays monotonic.
    narrative = _without_stance_lines(narrative)

    def pack(head_chars: int, tail_text: str, stance_lines: list[str]) -> str:
        if head_chars >= len(narrative):
            head = narrative
        elif head_chars <= 0:
            head = ""
        else:
            head = narrative[:head_chars].rstrip() + "…"
        parts: list[str] = []
        if head:
            parts.append(head)
        for line in stance_lines:
            if line not in head:
                parts.append(line)
        if tail_text and tail_text not in head:
            parts.append(tail_text)
        return "\n".join(parts)

    def fits(text: str) -> bool:
        dumped = json.dumps({**payload, "teamBriefing": text}, ensure_ascii=False, default=str)
        return len(dumped) <= limit

    tail_text = tail
    while tail_text and not fits(pack(0, tail_text, stances)):
        shrunk = _shrink_macro_json(tail_text, lambda item: fits(pack(0, item, stances)))
        if not shrunk or shrunk == tail_text:
            tail_text = ""
            break
        tail_text = shrunk
    stance_keep = list(stances)
    while stance_keep and not fits(pack(0, tail_text, stance_keep)):
        stance_keep.pop()
    if not fits(pack(0, tail_text, stance_keep)):
        return ""

    lo = 0
    hi = len(narrative)
    best = pack(0, tail_text, stance_keep)
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = pack(mid, tail_text, stance_keep)
        if fits(candidate):
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def split_trailing_json(briefing: str) -> tuple[str, str]:
    """Separate a trailing one-line JSON object, usually the macro-driver block."""
    stripped = briefing.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return "", stripped
    lines = briefing.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if not line:
            continue
        if not (line.startswith("{") and line.endswith("}")):
            break
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            break
        if isinstance(parsed, dict):
            narrative = "\n".join(lines[:index]).strip()
            return narrative, line
        break
    return briefing.strip(), ""


def _stance_lines(narrative: str) -> list[str]:
    found: list[str] = []
    for match in _STANCE_LINE.finditer(narrative):
        line = match.group(0).strip()
        if line not in found:
            found.append(line)
    return found


def _without_stance_lines(narrative: str) -> str:
    kept = [
        line
        for line in narrative.splitlines()
        if line.strip() and _STANCE_LINE.match(line.strip()) is None
    ]
    return "\n".join(kept)


def _shrink_macro_json(tail: str, fits_text: Callable[[str], bool]) -> str:
    """Drop macro-driver rows from the end until ``fits_text`` accepts the line."""
    try:
        data = json.loads(tail)
    except json.JSONDecodeError:
        return ""
    drivers = data.get("macroDrivers") if isinstance(data, dict) else None
    if not isinstance(drivers, list) or not drivers:
        return ""
    kept: list[Any] = []
    for item in drivers:
        trial = json.dumps({"macroDrivers": [*kept, item]}, ensure_ascii=False)
        if not fits_text(trial):
            break
        kept.append(item)
    if not kept:
        return ""
    return json.dumps({"macroDrivers": kept}, ensure_ascii=False)
