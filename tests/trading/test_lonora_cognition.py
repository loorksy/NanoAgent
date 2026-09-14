import json

import pytest

from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.providers.base import LLMResponse
from nanobot.trading.agents.apply_model_decision import (
    apply_model_decision,
    apply_revision,
    entry_print_state,
)
from nanobot.trading.agents.synthesizer import run_final_decision_synthesizer
from nanobot.trading.drawings.plan import build_drawing_plan
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.recommendations.store import latest_live_recommendation, store_recommendation
from nanobot.trading.recommendations.tradability import assess_plan_tradability
from nanobot.trading.turn_planner import plan_turn
from nanobot.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    Candle,
    EvidenceSnapshot,
    FinalDecisionResult,
    GateChainResult,
    GateVerdict,
    MarketSync,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    TradeCandidate,
    TradeValidationResult,
)


def _snapshot() -> EvidenceSnapshot:
    return EvidenceSnapshot(
        payload={
            "mtf": {"current_bias": "bearish", "conflict": False},
            "structure": {"trend": "downtrend"},
            "candidates": [
                {
                    "id": "cand-bear-1",
                    "action": "sell",
                    "entry": 2400.0,
                    "stopLoss": 2415.0,
                    "targets": [2380.0, 2360.0],
                    "entryType": "limit_touch",
                },
                {
                    "id": "cand-bull-1",
                    "action": "buy",
                    "entry": 2400.0,
                    "stopLoss": 2385.0,
                    "targets": [2420.0, 2440.0],
                    "entryType": "market",
                },
            ],
        },
        evidence_levels=[2360.0, 2380.0, 2385.0, 2400.0, 2415.0, 2420.0, 2440.0],
    )


def _parsed(**overrides):
    base = {
        "direction": "sell",
        "planType": "conditional",
        "selectedTradeCandidateId": "cand-bear-1",
        "proposedLevels": None,
        "activationCondition": "wait for 2400",
        "activationRule": {"kind": "price_touch", "level": 2400},
        "invalidationRule": "close above 2415",
        "alternativeScenario": "buy if demand holds",
        "validityCandles": 12,
        "confidence": 0.8,
        "summary": "Gold SELL from structure",
        "keyReasons": ["trend down"],
        "riskWarnings": [],
        "decisionTrace": {
            "hypotheses": [{"scenario": "sell continuation", "supporting": ["BOS"], "opposing": []}],
            "chosenBecause": "structure broke",
            "planTypeBecause": "waiting for retest",
        },
        "scenarioPath": [{"barsAhead": 2, "price": 2390, "label": "pullback"}, {"barsAhead": 8, "price": 2360}],
        "alternativeScenarioPath": [{"barsAhead": 3, "price": 2410}, {"barsAhead": 6, "price": 2415}],
    }
    base.update(overrides)
    return base


def test_apply_model_decision_follow_through_not_conditional() -> None:
    result = apply_model_decision(
        _parsed(),
        snapshot=_snapshot(),
        live_price=2396.0,
        atr=8.0,
        locale="en",
    )
    assert result.decision == "sell"
    assert result.plan_type == "immediate"
    assert result.recommendation.activation_rule is None
    assert result.recommendation.entry_type == "market"


def test_live_already_through_sell_entry() -> None:
    assert entry_print_state(direction="sell", entry=2400.0, live=2390.0) == "through"
    result = apply_model_decision(
        _parsed(planType="conditional"),
        snapshot=_snapshot(),
        live_price=2390.0,
        atr=8.0,
        locale="en",
    )
    assert result.plan_type == "immediate"


def test_ungrounded_proposed_levels_dropped() -> None:
    result = apply_model_decision(
        _parsed(
            selectedTradeCandidateId=None,
            proposedLevels={"entry": 99999, "stopLoss": 100000, "targets": [99000]},
        ),
        snapshot=_snapshot(),
        live_price=2400.0,
        atr=8.0,
        locale="en",
    )
    assert any("not grounded" in w.lower() or "الأدلة" in w for w in result.risk_warnings)
    assert result.recommendation.entry == 2400.0


def test_gate_veto_is_not_tradable() -> None:
    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="blocked",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell", entry=2400, stop_loss=2415, targets=[2380, 2360]
        ),
        gate_chain=GateChainResult(
            verdicts=[GateVerdict(id="G1", name="news", status="veto")],
            allowed=False,
            confidence_delta=-10,
            vetoed_by=GateVerdict(id="G1", name="news", status="veto", reason="news"),
        ),
    )
    ok, reason = assess_plan_tradability(decision)
    assert ok is False
    assert "veto" in reason


def test_direction_flip_on_reevaluation_refused() -> None:
    assert apply_revision("sell", "buy") == "sell"
    result = apply_model_decision(
        _parsed(direction="buy", selectedTradeCandidateId="cand-bull-1"),
        snapshot=_snapshot(),
        live_price=2400.0,
        atr=8.0,
        issued_side="sell",
        locale="en",
    )
    assert result.decision == "sell"


def test_scenario_path_pins_to_target_and_stop() -> None:
    result = apply_model_decision(
        _parsed(),
        snapshot=_snapshot(),
        live_price=2400.0,
        atr=8.0,
        locale="en",
    )
    rec = result.recommendation
    assert rec.scenario_path[-1].price == rec.targets[-1]
    assert rec.alternative_scenario_path[-1].price == rec.stop_loss
    assert len(rec.scenario_path) >= 2
    drawings = build_drawing_plan(
        StructureResult("downtrend", [], [], [], []),
        SupplyDemandResult([], None, None),
        result,
    )
    kinds = [d.semantic_role for d in drawings]
    assert "scenario_path" in kinds
    assert "alternative_scenario_path" in kinds


def test_plan_turn_followup_when_live() -> None:
    turn = plan_turn("اعطيني توصية", active_recommendation_live=True)
    assert turn.mode == "recommendation_followup"
    assert turn.requested_new_plan is True
    assert turn.tools.run_full_pipeline is False


@pytest.mark.asyncio
async def test_synthesizer_uses_fake_llm_not_selected_candidate() -> None:
    async def fake_complete(_messages):
        return json.dumps(_parsed(direction="buy", selectedTradeCandidateId="cand-bull-1", planType="immediate"))

    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
        quote_mid=2400.0,
    )
    risk = RiskAgentResult(
        proposed_trade=TradeCandidate("x", "sell", 2400, "market", 2415, [2380], 2, 0.9),
        validation=TradeValidationResult(accepted=True, reasons=[]),
        selected_candidate=TradeCandidate("cand-bear-1", "sell", 2400, "market", 2415, [2380], 2, 0.9),
        candidates=[
            TradeCandidate("cand-bull-1", "buy", 2400, "market", 2385, [2420, 2440], 2, 0.4),
            TradeCandidate("cand-bear-1", "sell", 2400, "market", 2415, [2380, 2360], 2, 0.9),
        ],
    )
    result = await run_final_decision_synthesizer(
        risk,
        StructureResult("downtrend", [], [], [], []),
        MultiTimeframeResult("bearish", "bearish", "bearish", False),
        NewsMacroResult("low", "unknown", [], [], True, ""),
        market=market,
        complete=fake_complete,
    )
    assert result.decision == "buy"
    assert result.recommendation.action == "buy"


def _synth_market() -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
        quote_mid=2400.0,
    )


def _synth_risk() -> RiskAgentResult:
    return RiskAgentResult(
        proposed_trade=TradeCandidate("x", "sell", 2400, "market", 2415, [2380], 2, 0.9),
        validation=TradeValidationResult(accepted=True, reasons=[]),
        selected_candidate=TradeCandidate("cand-bear-1", "sell", 2400, "market", 2415, [2380], 2, 0.9),
        candidates=[
            TradeCandidate("cand-bull-1", "buy", 2400, "market", 2385, [2420, 2440], 2, 0.4),
            TradeCandidate("cand-bear-1", "sell", 2400, "market", 2415, [2380, 2360], 2, 0.9),
        ],
    )


async def _synth_default_complete(**kwargs):
    return await run_final_decision_synthesizer(
        _synth_risk(),
        StructureResult("downtrend", [], [], [], []),
        MultiTimeframeResult("bearish", "bearish", "bearish", False),
        NewsMacroResult("low", "unknown", [], [], True, ""),
        market=_synth_market(),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_synthesizer_no_usable_decision_without_provider() -> None:
    """HTTP analyze used to skip request context; Lonora then WAIT @ 0.0."""
    result = await _synth_default_complete()
    assert result.decision == "wait"
    assert result.confidence == 0.0
    assert "synthesizer" in result.summary.lower()


@pytest.mark.asyncio
async def test_synthesizer_uses_bound_request_provider() -> None:
    from nanobot.utils.llm_runtime import LLMRuntime

    class _FakeProvider:
        async def chat(self, **_kwargs):
            return LLMResponse(content=json.dumps(_parsed()))

    runtime = LLMRuntime.capture(_FakeProvider(), "test-model", context_window_tokens=128_000)
    with request_context(RequestContext(channel="webui", chat_id="analyze", runtime=runtime)):
        result = await _synth_default_complete()
    assert result.decision == "sell"
    assert result.confidence > 0
    assert "no usable decision" not in result.summary.lower()


@pytest.mark.asyncio
async def test_live_plan_followup_does_not_call_synthesizer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.7,
        summary="live sell",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=2400,
            stop_loss=2415,
            targets=[2380, 2360],
            execution_state="valid_now",
        ),
    )
    rec_id = store_recommendation(decision, [], market, session_key="chat:1")
    assert rec_id
    assert latest_live_recommendation("chat:1") is not None

    called = {"n": 0}

    async def boom(_messages):
        called["n"] += 1
        raise AssertionError("synthesizer must not run on follow-up")

    result = await run_unified_chart_agent(
        store=True,
        session_key="chat:1",
        followup_only=True,
        complete=boom,
    )
    assert called["n"] == 0
    assert "متابعة" in result.decision.summary or "follow-up" in result.decision.summary.lower()
    assert result.team_mode == "followup"


@pytest.mark.asyncio
async def test_gate_veto_stores_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    decision = FinalDecisionResult(
        decision="wait",
        confidence=0.2,
        summary="veto",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="wait", entry=2400, stop_loss=2415, targets=[2380]),
        gate_chain=GateChainResult(
            verdicts=[],
            allowed=False,
            confidence_delta=0,
            vetoed_by=GateVerdict(id="G7", name="reprice", status="veto"),
        ),
    )
    assert store_recommendation(decision, [], market, session_key="chat:2") == ""
