"""Unified gold chart agent orchestrator — Lonora cognition order."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from nanobot.agent.tools.context import current_request_context
from nanobot.trading.agents.synthesizer import run_final_decision_synthesizer
from nanobot.trading.evidence import PipelineContext, run_evidence_graph
from nanobot.trading.cards.artifacts import apply_result_artifacts
from nanobot.trading.cards.derive import derive_cards
from nanobot.trading.intent_router import route_intent
from nanobot.trading.locale import locale_from_text
from nanobot.trading.drawings.plan import build_drawing_plan
from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.followup import grade_live_recommendation
from nanobot.trading.recommendations.store import latest_live_recommendation, store_recommendation
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.trading.stage_events import StageEvent, emit_stage
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, EntryPlan, FinalDecisionResult

StageEmitter = Callable[[StageEvent], None]


def _noop_emit(_: StageEvent) -> None:
    return None


def _wait_decision(summary: str, reason: str, interval: str = "15m") -> FinalDecisionResult:
    return FinalDecisionResult(
        decision="wait",
        confidence=0.0,
        summary=summary,
        key_reasons=[reason],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="wait", interval=interval),
        execution_state="blocked",
        refusal_summary=reason,
    )


def _session_key() -> str | None:
    ctx = current_request_context()
    return ctx.session_key if ctx else None


def _operator_text() -> str:
    ctx = current_request_context()
    return (ctx.original_user_text if ctx else "") or ""


async def run_unified_chart_agent(
    *,
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    team_mode: str = "core",
    emit: StageEmitter | None = None,
    store: bool = True,
    session_key: str | None = None,
    followup_only: bool = False,
    issued_side: str | None = None,
    team_briefing: str | None = None,
    complete: Any = None,
    visual_capture: Any = None,
) -> AgentFinalResult:
    emit_fn = emit or _noop_emit
    runtime = get_runtime_store().snapshot()
    key = session_key or _session_key()
    live = latest_live_recommendation(key) if key else None

    if followup_only or (live and issued_side is None):
        if not live:
            return AgentFinalResult(
                decision=_wait_decision("No live recommendation to follow up.", "no live plan", interval)
            )
        emit_fn(emit_stage("market_data", "running"))
        operator = _operator_text()
        graded = grade_live_recommendation(live, operator_text=operator)
        emit_fn(emit_stage("market_data", "done"))
        locale = locale_from_text(operator)
        result = AgentFinalResult(
            decision=graded,
            stages=[emit_stage("market_data", "done").to_wire()],
            team_mode="followup",
            recommendation_id=str(live.get("id")),
        )
        apply_result_artifacts(
            result,
            operator_text=operator,
            intent_kind="recommendation_followup",
            locale=locale,
            followup=True,
            plan_row=live,
        )
        result.cards = derive_cards(result, locale=locale)
        return result

    if runtime.kill_switch:
        return AgentFinalResult(decision=_wait_decision("Trading kill switch is active.", "Kill switch", interval))

    stages: list[dict[str, Any]] = []

    def track(event: StageEvent) -> None:
        stages.append(event.to_wire())
        emit_fn(event)

    pipeline = PipelineContext(
        symbol=symbol,
        interval=interval,
        visual_capture=visual_capture,
    )
    pipeline = await run_evidence_graph(pipeline, track=track)
    if pipeline.aborted or pipeline.market is None:
        market = pipeline.market
        reason = pipeline.abort_reason or "Market data sync failed"
        return AgentFinalResult(
            decision=_wait_decision(reason, reason, interval),
            market=market,
            stages=stages,
        )

    market = pipeline.market
    structure = pipeline.structure
    liquidity = pipeline.liquidity
    supply_demand = pipeline.supply_demand
    mtf = pipeline.mtf
    news = pipeline.news
    geometry = pipeline.geometry
    risk = pipeline.risk
    visual = pipeline.visual
    snapshots = pipeline.snapshots

    track(emit_stage("final_decision", "running"))
    decision = await run_final_decision_synthesizer(
        risk,
        structure,
        mtf,
        news,
        symbol,
        interval,
        market=market,
        liquidity=liquidity,
        supply_demand=supply_demand,
        geometry=geometry,
        visual=visual,
        visual_snapshots=snapshots,
        team_briefing=team_briefing,
        operator_text=_operator_text(),
        issued_side=issued_side,
        complete=complete,
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
        activation_rule=rec.activation_rule,
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
            visual=visual,
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
        decision.refusal_summary = (veto.reason_ar or veto.reason) if veto else "Gate veto"
        decision.summary = f"Recommendation blocked: {decision.refusal_summary}"
        decision.recommendation.action = "wait"
        decision.execution_state = "blocked"
        rec.execution_state = "blocked"
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
    drawings = build_drawing_plan(structure, supply_demand, decision, market=market)
    track(emit_stage("drawing", "done"))

    rec_id: str | None = None
    if store and not runtime.paused:
        rec_id = store_recommendation(decision, drawings, market, session_key=key)

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
        recommendation_id=rec_id,
        stages=stages,
        team_mode=team_mode,
        visual_snapshots=snapshots,
    )
    operator = _operator_text()
    locale = locale_from_text(operator)
    intent = route_intent(operator)
    result.cards = derive_cards(result, locale=locale)
    apply_result_artifacts(
        result,
        operator_text=operator,
        intent_kind=intent.kind,
        locale=locale,
    )
    return result
