"""Privileged trading kernel — synthesizer + G1–G20 gates + store.

Call sites (HTTP analyze, supersede approve, analyze_gold, run_trading_kernel tool)
must go through this function when LONORA_UNIFIED_LOOP is on. Does not import
or call MT5 execution helpers.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from nanobot.agent.tools.context import current_request_context
from nanobot.trading.agents.synthesizer import run_final_decision_synthesizer
from nanobot.trading.cards.artifacts import apply_result_artifacts
from nanobot.trading.cards.derive import derive_cards
from nanobot.trading.config import unified_loop_mode
from nanobot.trading.drawings.plan import build_drawing_plan
from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.evidence.node_sets import SYNTHESIS_REQUIRED_NODES
from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.gates.news_window import nearest_high_impact
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.gold import DATA_SYMBOL, require_gold
from nanobot.trading.i18n import gate_label, tr
from nanobot.trading.intel.postmortem import refuse_repeat_error
from nanobot.trading.intent_router import route_intent
from nanobot.trading.locale import locale_from_text
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.observability import log_gate_observability
from nanobot.trading.policy import GOLD_POINT
from nanobot.trading.policy_guard import PolicyViolation
from nanobot.trading.recommendations.lifecycle import close_plan_for_session, sync_session_live_plan
from nanobot.trading.recommendations.store import latest_live_recommendation, store_recommendation
from nanobot.trading.risk_state import get_risk_store
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.trading.stage_events import StageEvent, emit_stage
from nanobot.trading.turn_session import current_turn_session, require_turn_session
from nanobot.trading.types import (
    AgentFinalResult,
    AgentRecommendation,
    EntryPlan,
    FinalDecisionResult,
)
from nanobot.trading.unified_evidence import fetch_evidence_nodes, record_market_prices

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


def _session_key(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    ctx = current_request_context()
    return ctx.session_key if ctx else None


def _operator_text() -> str:
    ctx = current_request_context()
    return (ctx.original_user_text if ctx else "") or ""


def _record_plan_prices(result: AgentFinalResult) -> None:
    turn = current_turn_session()
    if turn is None:
        return
    rec = result.decision.recommendation
    for value in (rec.entry, rec.stop_loss, *(rec.targets or [])):
        if value is None:
            continue
        turn.add_price_strings(f"{float(value):.2f}")


async def run_trading_kernel(
    *,
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    team_mode: str = "core",
    store: bool = True,
    gather_missing: bool = True,
    session_key: str | None = None,
    issued_side: str | None = None,
    team_briefing: str | None = None,
    complete: Any = None,
    visual_capture: Any = None,
    pipeline: PipelineContext | None = None,
    emit: StageEmitter | None = None,
    present_ui: bool = True,
    reevaluate: bool = False,
    force_new_plan: bool = False,
) -> AgentFinalResult:
    """Run synthesizer + G1–G20 gates. Never places broker orders."""
    require_gold(symbol)
    symbol = DATA_SYMBOL
    emit_fn = emit or _noop_emit
    runtime = get_runtime_store().snapshot()
    key = _session_key(session_key)
    turn = current_turn_session() or require_turn_session()
    turn.session_key = key or turn.session_key
    turn.interval = interval

    if unified_loop_mode() == "shadow":
        store = False

    if key:
        sync_session_live_plan(key)

    if runtime.kill_switch:
        return AgentFinalResult(
            decision=_wait_decision("Trading kill switch is active.", "Kill switch", interval)
        )

    live = latest_live_recommendation(key) if key else None
    if live and not reevaluate and not force_new_plan:
        raise PolicyViolation(
            "This conversation already has a live recommendation. "
            "Use get_live_recommendation or pass force_new_plan=true.",
            plan=None,
        )
    if live and force_new_plan and key:
        closed = close_plan_for_session(
            key,
            status="superseded",
            reason="operator_force_new",
            category="modified",
        )
        if not closed.get("ok"):
            raise PolicyViolation("Could not close the active plan.", plan=None)
        live = None
    if reevaluate and live and issued_side is None:
        issued_side = str(live.get("direction") or "") or None

    stages: list[dict[str, Any]] = []

    def track(event: StageEvent) -> None:
        stages.append(event.to_wire())
        emit_fn(event)

    if pipeline is not None:
        turn.pipeline = pipeline
    ctx = turn.ensure_pipeline(interval=interval)
    if visual_capture is not None:
        ctx.visual_capture = visual_capture

    missing = sorted(SYNTHESIS_REQUIRED_NODES - turn.present_nodes())
    if missing:
        if not gather_missing:
            raise PolicyViolation(
                "Missing synthesis evidence nodes: " + ", ".join(missing),
                plan=None,
            )
        await fetch_evidence_nodes(
            list(SYNTHESIS_REQUIRED_NODES),
            interval=interval,
            session=turn,
            visual_capture=visual_capture,
        )
        ctx = turn.ensure_pipeline(interval=interval)
        turn.adjustments.append("injected_required_nodes:" + ",".join(missing))

    if ctx.aborted or ctx.market is None:
        reason = ctx.abort_reason or "Market data sync failed"
        return AgentFinalResult(
            decision=_wait_decision(reason, reason, interval),
            market=ctx.market,
            stages=stages,
        )

    market = ctx.market
    structure = ctx.structure
    liquidity = ctx.liquidity
    supply_demand = ctx.supply_demand
    mtf = ctx.mtf
    news = ctx.news
    geometry = ctx.geometry
    risk = ctx.risk
    visual = ctx.visual
    snapshots = ctx.snapshots
    record_market_prices(turn, ctx)

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
    turn.kernel_ran = True
    turn.kernel_decision = decision.decision

    if decision.decision == "wait":
        track(emit_stage("final_decision", "done"))
        result = AgentFinalResult(
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
        turn.kernel_result = result
        return result

    rec = decision.recommendation
    if rec.action in {"buy", "sell"}:
        setup = "structure"
        if structure is not None and structure.latest_structure_event is not None:
            setup = structure.latest_structure_event.type
        elif rec.plan_type:
            setup = rec.plan_type
        repeat = refuse_repeat_error(side=rec.action, setup=setup)
        if repeat is not None:
            loc = locale_from_text(_operator_text())
            reason = tr("lesson.repeat", loc, reason=repeat.reason)
            decision.decision = "wait"
            decision.refusal_summary = reason
            decision.summary = reason
            decision.recommendation.action = "wait"
            decision.execution_state = "blocked"
            rec.execution_state = "blocked"
            rec.action = "wait"
            turn.kernel_decision = "wait"
            track(emit_stage("final_decision", "failed"))
            result = AgentFinalResult(
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
            turn.kernel_result = result
            return result

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

    now_ms = int(time.time() * 1000)
    quote = fetch_quote(symbol)
    stored = get_risk_store().snapshot()
    spread = None
    if quote is not None and quote.bid is not None and quote.ask is not None:
        spread = abs(quote.ask - quote.bid) / GOLD_POINT
    minutes_to = minutes_since = None
    if news is not None:
        minutes_to, minutes_since = nearest_high_impact(news.upcoming_events, now_ms)
    risk_snap = RiskSnapshot(
        spread_points=spread,
        quote_age_seconds=0.0 if quote is not None else None,
        bid=quote.bid if quote else None,
        ask=quote.ask if quote else None,
        last_mid=stored.last_mid or None,
        current_mid=(quote.mid if quote and quote.mid else market.last_close),
        open_positions=stored.open_positions,
        open_buy_losing=stored.open_buy_losing,
        open_sell_losing=stored.open_sell_losing,
        daily_drawdown_pct=max(0.0, -float(stored.daily_pnl_pct or 0.0)),
        consecutive_losses=stored.consecutive_losses,
        cooldown_until_ms=stored.cooldown_until_ms,
        cooldown_reason=stored.cooldown_reason,
        kill_switch=runtime.kill_switch,
        emergency_lock=stored.emergency_lock,
        holiday=stored.holiday,
        news_day=stored.news_day or (news is not None and news.news_risk == "high"),
        atr=market.atr,
        atr_baseline=stored.atr_baseline or None,
        pending_created_ms=None,
        minutes_to_high_impact=minutes_to,
        minutes_since_high_impact=minutes_since,
        seconds_since_high_impact=None if minutes_since is None else minutes_since * 60,
        feature_toggles=dict(stored.feature_toggles),
    )

    gates = build_gates(
        GateInputs(
            now_ms=now_ms,
            news=news,
            structure=structure,
            liquidity=liquidity,
            supply_demand=supply_demand,
            mtf=mtf,
            plan=plan,
            atr=market.atr,
            visual=visual,
            fetch_live_price=fetch_live,
            risk=risk_snap,
        )
    )
    gate_chain = await run_gate_chain(gates)
    log_gate_observability(gate_chain)
    from nanobot.trading.gates.reprice_loop import apply_g7_reprice_loop

    gate_chain, plan, rec = await apply_g7_reprice_loop(gate_chain, gates, plan, rec)
    decision.recommendation = rec
    decision.gate_chain = gate_chain
    decision.confidence = max(0.05, decision.confidence + gate_chain.confidence_delta / 100)

    if not gate_chain.allowed:
        veto = gate_chain.vetoed_by
        loc = locale_from_text(_operator_text())
        reason = (veto.reason_ar or veto.reason) if veto else tr("synth.operational_blocker", loc)
        check = gate_label(veto.id, loc) if veto else ""
        decision.decision = "wait"
        decision.refusal_summary = reason
        decision.summary = (
            tr("gate.blocked", loc, check=check, reason=reason) if check else reason
        )
        decision.recommendation.action = "wait"
        decision.execution_state = "blocked"
        rec.execution_state = "blocked"
        turn.kernel_decision = "wait"
        track(emit_stage("final_decision", "failed"))
        result = AgentFinalResult(
            decision=decision,
            structure=structure,
            liquidity=liquidity,
            supply_demand=supply_demand,
            mtf=mtf,
            news=news,
            risk=risk_snap,
            market=market,
            stages=stages,
            team_mode=team_mode,
        )
        turn.kernel_result = result
        return result

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
        risk=risk_snap,
        market=market,
        drawings=drawings,
        recommendation_id=rec_id,
        stages=stages,
        team_mode=team_mode,
        visual_snapshots=snapshots,
    )
    if present_ui:
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
    _record_plan_prices(result)
    turn.kernel_result = result
    turn.kernel_decision = decision.decision
    return result
