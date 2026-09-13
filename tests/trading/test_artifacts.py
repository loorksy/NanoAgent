from nanobot.trading.cards.artifacts import emit_trading_artifacts
from nanobot.trading.types import (
    AgentFinalResult,
    AgentRecommendation,
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
