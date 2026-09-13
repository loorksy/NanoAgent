from nanobot.trading.recommendations.followup import refresh_recommendation_outcomes
from nanobot.trading.recommendations.outcome_alerts import (
    OutcomeTransition,
    format_outcome_alert,
    should_alert_transition,
)
from nanobot.trading.recommendations.store import store_recommendation
from nanobot.trading.types import (
    AgentFinalResult,
    AgentMarketContext,
    AgentRecommendation,
    FinalDecisionResult,
    MarketSync,
)


def _market() -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[],
        last_close=2650.0,
        atr=5.0,
        sync=MarketSync(ok=True),
    )


def _decision(direction: str = "buy") -> FinalDecisionResult:
    return FinalDecisionResult(
        decision=direction,
        confidence=0.7,
        summary="Test plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action=direction,
            entry=2650.0,
            stop_loss=2640.0,
            targets=[2660.0, 2670.0],
            execution_state="valid_now",
            interval="15m",
        ),
    )


def test_should_alert_on_tp1_transition():
    transition = OutcomeTransition(
        rec_id="r1",
        previous="in_trade",
        current="tp1",
        row={"direction": "buy"},
    )
    assert should_alert_transition(transition)


def test_should_not_alert_on_waiting_to_valid_now():
    transition = OutcomeTransition(
        rec_id="r1",
        previous="valid_now",
        current="waiting",
        row={"direction": "buy"},
    )
    assert not should_alert_transition(transition)


def test_format_outcome_alert_arabic_html():
    text = format_outcome_alert(
        {
            "direction": "buy",
            "entry": 2650.0,
            "stop_loss": 2640.0,
            "targets": [2660.0],
            "summary": "Pullback entry",
        },
        "tp1",
        live_price=2661.0,
        html_mode=True,
    )
    assert "تحديث توصية الذهب" in text
    assert "هدف 1 تحقق" in text
    assert "$2,661.00" in text


def test_refresh_recommendation_outcomes_records_transition(monkeypatch):
    rec_id = store_recommendation(
        _decision(),
        [],
        _market(),
        session_key="test-session",
    )
    assert rec_id

    monkeypatch.setattr(
        "nanobot.trading.recommendations.followup.grade_outcome_status",
        lambda row, live_price=None: "tp1",
    )

    counts, transitions = refresh_recommendation_outcomes(live_price=2661.0)
    assert counts["updated"] == 1
    assert transitions
    assert transitions[0].current == "tp1"
