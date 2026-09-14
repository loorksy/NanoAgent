from nanobot.trading.recommendations.followup import (
    CLOSED_OUTCOME_STATUSES,
    LIVE_OUTCOME_STATUSES,
    grade_live_recommendation,
    grade_outcome_status,
)


def test_grade_outcome_status_buy_tp1():
    row = {
        "direction": "buy",
        "entry": 100.0,
        "stop_loss": 95.0,
        "targets": [110.0],
        "status": "valid_now",
    }
    assert grade_outcome_status(row, live_price=111.0) == "tp1"


def test_grade_outcome_status_sell_invalidated():
    row = {
        "direction": "sell",
        "entry": 100.0,
        "stop_loss": 102.0,
        "targets": [95.0],
        "status": "in_trade",
    }
    assert grade_outcome_status(row, live_price=103.0) == "invalidated"


def test_live_and_closed_sets():
    assert "in_trade" in LIVE_OUTCOME_STATUSES
    assert "tp1" in CLOSED_OUTCOME_STATUSES


def test_followup_summary_uses_arabic_labels():
    row = {
        "direction": "sell",
        "entry": 2400.0,
        "stop_loss": 2415.0,
        "targets": [2380.0],
        "status": "in_trade",
        "confidence": 0.7,
        "summary": "Sell plan",
        "interval": "15m",
    }
    graded = grade_live_recommendation(row, operator_text="حالة التوصية", live_price=2390.0)
    assert "SELL" not in graded.summary
    assert "in_trade" not in graded.summary
    assert "بيع" in graded.summary
    assert "داخل الصفقة" in graded.summary
