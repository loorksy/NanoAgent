"""Build G1-G20 gate definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from nanobot.trading.agents.news_macro import news_provider_configured
from nanobot.trading.gates.bad_tick import evaluate_bad_tick
from nanobot.trading.gates.cooldown_lock import evaluate_cooldown_lock
from nanobot.trading.gates.drawdown_breaker import evaluate_drawdown_breaker
from nanobot.trading.gates.entry_semantics import validate_entry_coherence
from nanobot.trading.gates.margin_guard import evaluate_margin_guard
from nanobot.trading.gates.max_positions import evaluate_max_positions
from nanobot.trading.gates.news_operational import evaluate_news_operational
from nanobot.trading.gates.news_policy import news_gate_mode
from nanobot.trading.gates.news_window import evaluate_news_window
from nanobot.trading.gates.pending_ttl import evaluate_pending_ttl
from nanobot.trading.gates.plan_alignment import (
    evaluate_liquidity_alignment,
    evaluate_supply_demand_alignment,
)
from nanobot.trading.gates.position_sizing import evaluate_position_sizing
from nanobot.trading.gates.revalidation import revalidate_plan
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.gates.rr_filter import evaluate_rr_filter
from nanobot.trading.gates.session_lock import evaluate_session_lock
from nanobot.trading.gates.slippage_guard import evaluate_slippage_guard
from nanobot.trading.gates.spread_guard import evaluate_spread_guard
from nanobot.trading.gates.stale_quote import evaluate_stale_quote
from nanobot.trading.i18n import gate_label
from nanobot.trading.types import (
    EntryPlan,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    StructureResult,
    SupplyDemandResult,
    VisualReview,
)

GATE_REQUIRED = {
    "G1": True,
    "G2": False,
    "G3": False,
    "G4": True,
    "G6": True,
    "G7": True,
    "G8": True,
    "G9": False,
    "G10": True,
    "G11": True,
    "G12": True,
    "G13": False,
    "G14": False,
    "G15": True,
    "G16": False,
    "G17": True,
    "G18": False,
    "G19": False,
    "G20": False,
}

_TOGGLE_FOR_GATE = {
    "G1": "news_shield",
    "G8": "rr_filter",
    "G9": "spread_guard",
    "G10": "cooldown_lock",
    "G11": "max_positions",
    "G12": "drawdown_breaker",
    "G13": "stale_quote",
    "G15": "session_lock",
    "G16": "bad_tick",
    "G17": "news_shield",
}


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
    risk: RiskSnapshot | None = None


def _skipped(toggle: str) -> dict[str, Any]:
    return {"status": "pass", "evidence": {toggle: "off"}}


def build_gates(inp: GateInputs) -> list[GateDefinition]:
    def _enabled(gate_id: str) -> bool:
        toggle = _TOGGLE_FOR_GATE.get(gate_id)
        if not toggle or inp.risk is None:
            return True
        return inp.risk.toggle(toggle)

    async def g1() -> dict[str, Any]:
        if not _enabled("G1"):
            return _skipped("news_shield")
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

    async def g8() -> dict[str, Any]:
        if not _enabled("G8"):
            return _skipped("rr_filter")
        return evaluate_rr_filter(inp.plan).as_raw()

    async def g9() -> dict[str, Any]:
        if not _enabled("G9"):
            return _skipped("spread_guard")
        return evaluate_spread_guard(inp.risk).as_raw()

    async def g10() -> dict[str, Any]:
        if not _enabled("G10"):
            return _skipped("cooldown_lock")
        return evaluate_cooldown_lock(inp.risk, now_ms=inp.now_ms).as_raw()

    async def g11() -> dict[str, Any]:
        if not _enabled("G11"):
            return _skipped("max_positions")
        return evaluate_max_positions(inp.plan, inp.risk).as_raw()

    async def g12() -> dict[str, Any]:
        if not _enabled("G12"):
            return _skipped("drawdown_breaker")
        return evaluate_drawdown_breaker(inp.risk).as_raw()

    async def g13() -> dict[str, Any]:
        if not _enabled("G13"):
            return _skipped("stale_quote")
        return evaluate_stale_quote(inp.risk).as_raw()

    async def g14() -> dict[str, Any]:
        live = inp.risk.current_mid if inp.risk is not None else None
        return evaluate_pending_ttl(
            inp.plan, inp.risk, now_ms=inp.now_ms, live_price=live
        ).as_raw()

    async def g15() -> dict[str, Any]:
        if not _enabled("G15"):
            return _skipped("session_lock")
        return evaluate_session_lock(inp.risk, now_ms=inp.now_ms).as_raw()

    async def g16() -> dict[str, Any]:
        if not _enabled("G16"):
            return _skipped("bad_tick")
        return evaluate_bad_tick(inp.risk).as_raw()

    async def g17() -> dict[str, Any]:
        if not _enabled("G17"):
            return _skipped("news_shield")
        return evaluate_news_operational(inp.plan, inp.risk).as_raw()

    async def g18() -> dict[str, Any]:
        return evaluate_margin_guard(inp.risk).as_raw()

    async def g19() -> dict[str, Any]:
        return evaluate_slippage_guard(inp.risk).as_raw()

    async def g20() -> dict[str, Any]:
        return evaluate_position_sizing(inp.plan, inp.risk).as_raw()

    return [
        GateDefinition("G1", gate_label("G1", "en"), g1),
        GateDefinition("G2", gate_label("G2", "en"), g2),
        GateDefinition("G3", gate_label("G3", "en"), g3),
        GateDefinition("G4", gate_label("G4", "en"), g4),
        GateDefinition("G6", gate_label("G6", "en"), g6),
        GateDefinition("G7", gate_label("G7", "en"), g7),
        GateDefinition("G8", gate_label("G8", "en"), g8),
        GateDefinition("G9", gate_label("G9", "en"), g9),
        GateDefinition("G10", gate_label("G10", "en"), g10),
        GateDefinition("G11", gate_label("G11", "en"), g11),
        GateDefinition("G12", gate_label("G12", "en"), g12),
        GateDefinition("G13", gate_label("G13", "en"), g13),
        GateDefinition("G14", gate_label("G14", "en"), g14),
        GateDefinition("G15", gate_label("G15", "en"), g15),
        GateDefinition("G16", gate_label("G16", "en"), g16),
        GateDefinition("G17", gate_label("G17", "en"), g17),
        GateDefinition("G18", gate_label("G18", "en"), g18),
        GateDefinition("G19", gate_label("G19", "en"), g19),
        GateDefinition("G20", gate_label("G20", "en"), g20),
    ]
