"""Build G1-G7 gate definitions."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from nanobot.trading.agents.news_macro import news_provider_configured
from nanobot.trading.gates.entry_semantics import validate_entry_coherence
from nanobot.trading.gates.news_policy import news_gate_mode
from nanobot.trading.gates.news_window import evaluate_news_window
from nanobot.trading.gates.plan_alignment import (
    evaluate_liquidity_alignment,
    evaluate_supply_demand_alignment,
)
from nanobot.trading.gates.revalidation import revalidate_plan
from nanobot.trading.i18n import gate_label
from nanobot.trading.types import (
    EntryPlan,
    GateStatus,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    StructureResult,
    SupplyDemandResult,
    VisualReview,
)

GATE_REQUIRED = {"G1": True, "G2": False, "G3": False, "G4": True, "G6": True, "G7": True}


@dataclass
class GateDefinition:
    id: str
    name: str
    run: Callable[[], Awaitable[dict[str, Any]]]


@dataclass
class GateInputs:
    now_ms: int
    news: NewsMacroResult | None
    structure: StructureResult | None
    liquidity: LiquidityResult | None
    supply_demand: SupplyDemandResult | None
    mtf: MultiTimeframeResult | None
    plan: EntryPlan
    atr: float
    visual: VisualReview | None
    fetch_live_price: Callable[[], float | None]


def build_gates(inp: GateInputs) -> list[GateDefinition]:
    async def g1() -> dict[str, Any]:
        mode = news_gate_mode()
        if mode == "off":
            return {"status": "pass", "confidence_delta": 0, "evidence": {"news_risk": "skipped"}}

        def _warn_unconfigured(reason_ar: str) -> dict[str, Any]:
            if mode == "strict":
                return {"status": "unavailable", "reason_ar": reason_ar}
            return {
                "status": "warn",
                "reason_ar": reason_ar,
                "confidence_delta": -8,
                "evidence": {"news_risk": "unknown", "policy": mode},
            }

        if not news_provider_configured():
            return _warn_unconfigured("News calendar not configured")
        if inp.news is None:
            return _warn_unconfigured("News data unavailable")
        if inp.news.news_risk == "unknown":
            return _warn_unconfigured(inp.news.reason or "News risk unknown")
        verdict = evaluate_news_window(inp.news.upcoming_events, inp.now_ms)
        if verdict.blocked:
            return {
                "status": "veto",
                "reason_ar": f"High-impact news window ({verdict.minutes_until_clear}m)",
                "evidence": {"event": verdict.event.title if verdict.event else None},
            }
        return {
            "status": "pass",
            "confidence_delta": -10 if inp.news.news_risk == "high" else 0,
            "evidence": {"news_risk": inp.news.news_risk},
        }

    async def g2() -> dict[str, Any]:
        if inp.liquidity is None:
            return {"status": "unavailable", "reason_ar": "Liquidity map missing"}
        status, reason = evaluate_liquidity_alignment(inp.plan, inp.liquidity, inp.atr)
        if status == "veto":
            return {"status": "veto", "reason_ar": reason}
        return {"status": "pass"}

    async def g3() -> dict[str, Any]:
        if inp.supply_demand is None:
            return {"status": "unavailable", "reason_ar": "Supply/demand missing"}
        status, reason = evaluate_supply_demand_alignment(inp.plan, inp.supply_demand)
        if status == "veto":
            return {"status": "veto", "reason_ar": reason}
        return {"status": "pass"}

    async def g4() -> dict[str, Any]:
        if inp.structure is None:
            return {"status": "unavailable", "reason_ar": "Structure missing"}
        delta = 0
        if inp.mtf and inp.mtf.conflict:
            delta -= 10
        visual = inp.visual
        if visual is None or visual.state == "not_checked":
            delta -= 15
        elif visual.state == "partial":
            delta -= 10
        return {"status": "pass", "confidence_delta": delta}

    async def g6() -> dict[str, Any]:
        ok, reasons = validate_entry_coherence(inp.plan, inp.atr)
        if not ok:
            return {"status": "veto", "reason_ar": "; ".join(reasons)}
        return {"status": "pass"}

    async def g7() -> dict[str, Any]:
        live = inp.fetch_live_price()
        result = revalidate_plan(inp.plan, live, inp.atr)
        if result.status == "unavailable":
            return {"status": "unavailable", "reason_ar": result.reason}
        if result.status in ("invalidated", "targets_passed"):
            return {"status": "veto", "reason_ar": result.reason}
        if result.status == "reanchored":
            return {
                "status": "pass",
                "confidence_delta": -5,
                "evidence": {"reanchored_entry": result.reanchored_entry},
            }
        return {"status": "pass"}

    return [
        GateDefinition("G1", gate_label("G1", "en"), g1),
        GateDefinition("G2", gate_label("G2", "en"), g2),
        GateDefinition("G3", gate_label("G3", "en"), g3),
        GateDefinition("G4", gate_label("G4", "en"), g4),
        GateDefinition("G6", gate_label("G6", "en"), g6),
        GateDefinition("G7", gate_label("G7", "en"), g7),
    ]
