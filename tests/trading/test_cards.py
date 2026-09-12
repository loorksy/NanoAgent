from nanobot.trading.cards.derive import derive_cards
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult


def test_derive_cards_decision_only():
    decision = FinalDecisionResult(
        decision="wait",
        confidence=0.4,
        summary="No setup",
        key_reasons=["test"],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="wait"),
    )
    cards = derive_cards(AgentFinalResult(decision=decision))
    kinds = [c["kind"] for c in cards]
    assert "decision" in kinds
