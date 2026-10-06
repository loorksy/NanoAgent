from mokli.trading.recommendations.followup import refresh_recommendation_outcomes
from mokli.trading.recommendations.outcome_alerts import (
    OutcomeTransition,
    format_outcome_alert,
    should_alert_transition,
)
from mokli.trading.recommendations.store import store_recommendation
from mokli.trading.types import (
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
        locale="ar",
    )
    assert "تحديث توصية الذهب" in text
    assert "تحقق الهدف الأول" in text
    assert "$2661.00" in text


def test_format_outcome_alert_english_html():
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
        locale="en",
    )
    assert "Gold recommendation update" in text
    assert "First target reached" in text


def test_refresh_recommendation_outcomes_records_transition(monkeypatch):
    rec_id = store_recommendation(
        _decision(),
        [],
        _market(),
        session_key="test-session",
    )
    assert rec_id

    monkeypatch.setattr(
        "mokli.trading.recommendations.followup.grade_outcome_status",
        lambda row, live_price=None, price_known=False: "tp1",
    )

    counts, transitions = refresh_recommendation_outcomes(live_price=2661.0)
    assert counts["updated"] == 1
    assert transitions
    assert transitions[0].current == "tp1"


def test_missing_price_does_not_fetch_once_per_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    for index in range(3):
        assert store_recommendation(
            _decision(),
            [],
            _market(),
            session_key=f"websocket:batch-{index}",
        )

    calls = {"direct": 0}

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("one quote per row")

    monkeypatch.setattr("mokli.trading.recommendations.followup.fetch_quote", _direct)
    refresh_recommendation_outcomes(live_price=None)
    assert calls == {"direct": 0}


def test_outcome_alerts_read_the_analysis_quote_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    for index in range(3):
        assert store_recommendation(
            _decision(),
            [],
            _market(),
            session_key=f"websocket:alerts-{index}",
        )

    from mokli.trading.recommendations.outcome_delivery import collect_outcome_web_alerts

    calls = {"live": 0, "direct": 0}

    def _live(*_args: object, **_kwargs: object) -> None:
        calls["live"] += 1
        return None

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr(
        "mokli.trading.recommendations.outcome_delivery.live_analysis_quote",
        _live,
    )
    monkeypatch.setattr("mokli.trading.recommendations.followup.fetch_quote", _direct)
    assert collect_outcome_web_alerts() == []
    assert calls == {"live": 1, "direct": 0}
