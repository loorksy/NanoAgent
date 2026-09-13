from nanobot.trading.agents.apply_model_decision import apply_model_decision
from nanobot.trading.cards.artifacts import (
    apply_result_artifacts,
    build_price_quote_artifacts,
    emit_trading_artifacts,
    infer_operator_artifacts,
    parse_artifacts_requested,
)
from nanobot.trading.types import (
    AgentFinalResult,
    AgentRecommendation,
    EvidenceSnapshot,
    FinalDecisionResult,
    GateChainResult,
    GateVerdict,
)


def _result(decision: str = "sell") -> AgentFinalResult:
    return AgentFinalResult(
        decision=FinalDecisionResult(
            decision=decision,
            confidence=0.7,
            summary="Gold SELL setup",
            key_reasons=["Structure trend: down"],
            risk_warnings=[],
            recommendation=AgentRecommendation(
                action=decision,
                entry=2650.0,
                stop_loss=2660.0,
                targets=[2640.0, 2630.0],
                interval="15m",
            ),
            gate_chain=GateChainResult(
                allowed=True,
                confidence_delta=0,
                verdicts=[
                    GateVerdict(id="G1", name="News", status="pass", reason_ar="ok"),
                ],
            ),
        ),
        visual_snapshots=[{"timeframe": "15m", "image": "data:image/jpeg;base64,abc"}],
    )


def test_parse_artifacts_requested_normalizes() -> None:
    assert parse_artifacts_requested(["decision", "level-map", "invalid", "decision"]) == [
        "decision",
        "level_map",
    ]


def test_emit_artifacts_caps_at_four() -> None:
    arts = emit_trading_artifacts(_result(), intent_kind="recommendation", locale="en")
    assert 1 <= len(arts) <= 4
    kinds = {art["type"] for art in arts}
    assert "decision" in kinds
    assert "level_map" in kinds


def test_chart_only_returns_snapshot() -> None:
    arts = emit_trading_artifacts(
        _result(),
        intent_kind="chart_image",
        locale="en",
        chart_only=True,
    )
    assert len(arts) == 1
    assert arts[0]["type"] == "chart_snapshot"


def test_llm_requested_subset() -> None:
    arts = emit_trading_artifacts(
        _result(),
        intent_kind="recommendation",
        locale="en",
        requested=["key_reasons", "level_map"],
    )
    kinds = [art["type"] for art in arts]
    assert kinds == ["decision", "key_reasons", "level_map"]


def test_llm_invalid_request_falls_back_to_default() -> None:
    arts = emit_trading_artifacts(
        _result(),
        intent_kind="recommendation",
        locale="en",
        requested=["not_a_real_type"],
    )
    kinds = {art["type"] for art in arts}
    assert "decision" in kinds
    assert "level_map" in kinds


def test_chart_image_intent_forces_snapshot() -> None:
    arts = emit_trading_artifacts(
        _result(),
        intent_kind="chart_image",
        locale="en",
        requested=["decision", "level_map"],
    )
    assert len(arts) == 1
    assert arts[0]["type"] == "chart_snapshot"


def test_infer_price_query_artifacts() -> None:
    assert infer_operator_artifacts("gold price", "price_query") == ["price_quote"]


def test_infer_followup_status_artifacts() -> None:
    picks = infer_operator_artifacts("ما حالة الخطة؟", "gold_analysis", followup=True)
    assert picks == ["plan_status", "tracked_plan"]


def test_build_price_quote_artifact() -> None:
    arts = build_price_quote_artifacts(
        {"symbol": "XAUUSD", "bid": 1.0, "ask": 2.0, "mid": 1.5, "tradeable": True},
        locale="en",
    )
    assert len(arts) == 1
    assert arts[0]["type"] == "price_quote"
    assert arts[0]["payload"]["mid"] == 1.5


def test_apply_result_artifacts_followup() -> None:
    result = _result()
    result.recommendation_id = "rec-1"
    plan_row = {
        "id": "rec-1",
        "direction": "sell",
        "entry": 2650.0,
        "stop_loss": 2660.0,
        "targets": [2640.0],
        "status": "waiting",
    }
    apply_result_artifacts(
        result,
        operator_text="what is the plan status?",
        intent_kind="recommendation_followup",
        locale="en",
        followup=True,
        plan_row=plan_row,
    )
    kinds = {art["type"] for art in result.artifacts}
    assert "plan_status" in kinds
    assert "tracked_plan" in kinds


def test_apply_model_decision_parses_artifacts_requested() -> None:
    parsed = {
        "direction": "sell",
        "planType": "immediate",
        "selectedTradeCandidateId": "cand-bear-1",
        "proposedLevels": None,
        "confidence": 0.6,
        "summary": "Sell gold",
        "keyReasons": ["Trend down"],
        "riskWarnings": [],
        "artifactsRequested": ["level_map", "key_reasons"],
    }
    snapshot = EvidenceSnapshot(
        payload={
            "tradeCandidates": [
                {
                    "id": "cand-bear-1",
                    "direction": "sell",
                    "entry": 2650.0,
                    "stop": 2660.0,
                    "targets": [2640.0, 2630.0],
                }
            ],
            "evidenceLevels": [2650.0, 2660.0, 2640.0, 2630.0],
        },
        evidence_levels=[2650.0, 2660.0, 2640.0, 2630.0],
    )
    decision = apply_model_decision(
        parsed,
        snapshot=snapshot,
        live_price=2649.0,
        atr=5.0,
        interval="15m",
        locale="en",
    )
    assert decision.artifacts_requested == ["level_map", "key_reasons"]
