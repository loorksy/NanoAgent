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


def test_derive_cards_includes_macro_drivers():
    decision = FinalDecisionResult(
        decision="buy",
        confidence=0.7,
        summary="buy",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="buy"),
    )
    cards = derive_cards(
        AgentFinalResult(
            decision=decision,
            macro_drivers=[
                {
                    "driver": "dxy",
                    "bias": "bullish",
                    "strength": 60,
                    "one_line_rationale": "weaker dollar",
                    "ran": True,
                    "reason": "cache_miss",
                }
            ],
        )
    )
    macro = next(c for c in cards if c["kind"] == "macro_drivers")
    assert macro["drivers"][0]["name"] == "dxy"
