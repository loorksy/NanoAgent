from nanobot.trading.agents.apply_model_decision import apply_model_decision
from nanobot.trading.cards.artifacts import (
    emit_trading_artifacts,
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
