"""Unified gold chart agent orchestrator."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from typing import Any

from nanobot.trading.agents.liquidity import run_liquidity_agent
from nanobot.trading.agents.market_data import run_market_data_agent
from nanobot.trading.agents.multi_timeframe import run_multi_timeframe_agent
from nanobot.trading.agents.news_macro import run_news_macro_agent
from nanobot.trading.agents.risk import run_risk_agent
from nanobot.trading.agents.structure import run_structure_agent
from nanobot.trading.agents.supply_demand import run_supply_demand_agent
from nanobot.trading.agents.synthesizer import run_final_decision_synthesizer
from nanobot.trading.cards.derive import derive_cards
from nanobot.trading.drawings.plan import build_drawing_plan
from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.store import store_recommendation
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.trading.stage_events import StageEvent, emit_stage
from nanobot.trading.types import AgentFinalResult, EntryPlan, FinalDecisionResult


StageEmitter = Callable[[StageEvent], None]


def _noop_emit(_: StageEvent) -> None:
    return None


async def run_unified_chart_agent(
    *,
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    team_mode: str = "core",
    emit: StageEmitter | None = None,
    store: bool = True,
) -> AgentFinalResult:
    emit_fn = emit or _noop_emit
    runtime = get_runtime_store().snapshot()
    if runtime.kill_switch:
        wait = FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary="Trading kill switch is active.",
            key_reasons=["Kill switch"],
            risk_warnings=[],
            recommendation=__import__("nanobot.trading.types", fromlist=["AgentRecommendation"]).AgentRecommendation(action="wait"),
            refusal_summary="Kill switch active",
        )
        return AgentFinalResult(decision=wait)

    stages: list[dict[str, Any]] = []

    def track(event: StageEvent) -> None:
        stages.append(event.to_wire())
        emit_fn(event)

    # Market data
    ev = emit_stage("market_data", "running")
    track(ev)
    market = await asyncio.to_thread(run_market_data_agent, symbol, interval)
    if not market.sync.ok:
        track(emit_stage("market_data", "failed"))
        wait = FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=market.sync.reason or "Market data sync failed",
            key_reasons=[market.sync.reason],
            risk_warnings=[],
            recommendation=__import__("nanobot.trading.types", fromlist=["AgentRecommendation"]).AgentRecommendation(action="wait"),
            refusal_summary=market.sync.reason,
        )
        return AgentFinalResult(decision=wait, market=market, stages=stages)
    track(emit_stage("market_data", "done"))

    # Parallel fleet
    fleet_stages = ("structure", "liquidity", "supply_demand", "multi_timeframe")
    for name in fleet_stages:
        track(emit_stage(name, "running"))

    structure, liquidity, supply_demand, mtf = await asyncio.gather(
        asyncio.to_thread(run_structure_agent, market),
        asyncio.to_thread(run_liquidity_agent, market),
        asyncio.to_thread(run_supply_demand_agent, market),
        asyncio.to_thread(run_multi_timeframe_agent, market),
    )
    for name in fleet_stages:
        track(emit_stage(name, "done"))

    track(emit_stage("news", "running"))
    news = await asyncio.to_thread(run_news_macro_agent)
    track(emit_stage("news", "done"))

    track(emit_stage("risk", "running"))
    risk = await asyncio.to_thread(run_risk_agent, market, structure, supply_demand)
    track(emit_stage("risk", "done"))

    track(emit_stage("final_decision", "running"))
    decision = await asyncio.to_thread(
        run_final_decision_synthesizer, risk, structure, mtf, news, symbol, interval
    )

    if decision.decision == "wait":
        track(emit_stage("final_decision", "done"))
        return AgentFinalResult(
            decision=decision,
            structure=structure,
            liquidity=liquidity,
            supply_demand=supply_demand,
            mtf=mtf,
            news=news,
            risk=risk,
            market=market,
            stages=stages,
            team_mode=team_mode,
        )

    rec = decision.recommendation
    plan = EntryPlan(
        direction=rec.action,  # type: ignore[arg-type]
        entry_type=rec.entry_type or "market",
        entry=rec.entry or market.last_close,
        stop_loss=rec.stop_loss or market.last_close,
        targets=rec.targets,
    )

    def fetch_live() -> float | None:
        q = fetch_quote(symbol)
        return q.mid if q else None

    gates = build_gates(
        GateInputs(
            now_ms=int(time.time() * 1000),
            news=news,
            structure=structure,
            liquidity=liquidity,
            supply_demand=supply_demand,
            mtf=mtf,
            plan=plan,
            atr=market.atr,
            visual_timeframes=[interval],
            fetch_live_price=fetch_live,
        )
    )
    gate_chain = await run_gate_chain(gates)
    from nanobot.trading.gates.reprice_loop import apply_g7_reprice_loop

    gate_chain, plan, rec = await apply_g7_reprice_loop(gate_chain, gates, plan, rec)
    decision.recommendation = rec
    decision.gate_chain = gate_chain
    decision.confidence = max(0.05, decision.confidence + gate_chain.confidence_delta / 100)

    if not gate_chain.allowed:
        veto = gate_chain.vetoed_by
        decision.decision = "wait"
        decision.refusal_summary = veto.reason_ar if veto else "Gate veto"
        decision.summary = f"Recommendation blocked: {decision.refusal_summary}"
        decision.recommendation.action = "wait"
        decision.execution_state = "blocked"
        track(emit_stage("final_decision", "failed"))
        return AgentFinalResult(
            decision=decision,
            structure=structure,
            liquidity=liquidity,
            supply_demand=supply_demand,
            mtf=mtf,
            news=news,
            risk=risk,
            market=market,
            stages=stages,
            team_mode=team_mode,
        )

    track(emit_stage("final_decision", "done"))

    track(emit_stage("drawing", "running"))
    drawings = build_drawing_plan(structure, supply_demand, decision)
    track(emit_stage("drawing", "done"))

    rec_id: str | None = None
    if store and not runtime.paused:
        rec_id = store_recommendation(decision, drawings, market)

    result = AgentFinalResult(
        decision=decision,
        structure=structure,
        liquidity=liquidity,
        supply_demand=supply_demand,
        mtf=mtf,
        news=news,
        risk=risk,
        market=market,
        drawings=drawings,
        cards=derive_cards(
            AgentFinalResult(
                decision=decision,
                structure=structure,
                liquidity=liquidity,
                supply_demand=supply_demand,
                mtf=mtf,
                news=news,
                risk=risk,
                market=market,
                drawings=drawings,
                recommendation_id=rec_id,
                stages=stages,
                team_mode=team_mode,
            )
        ),
        recommendation_id=rec_id,
        stages=stages,
        team_mode=team_mode,
    )
    return result
