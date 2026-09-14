"""Explicit new-recommendation requests vs live-plan guard."""

import asyncio

import pytest

from nanobot.trading.fast_path import try_gold_fast_path
from nanobot.trading.operator_keywords import wants_explicit_new_analysis
from nanobot.trading.recommendations.followup import (
    explain_new_rec_blocked,
    finalize_live_plan_if_closed,
    grade_live_recommendation,
)
from nanobot.trading.turn_planner import plan_turn


def test_wants_explicit_new_analysis_arabic_variants() -> None:
    assert wants_explicit_new_analysis("لا بدي توصية جديده")
    assert wants_explicit_new_analysis("اعطني توصية لشوف")
    assert wants_explicit_new_analysis("اعطيني توصية جديدة")


def test_plan_turn_marks_requested_new_plan() -> None:
    turn = plan_turn("لا بدي توصية جديده", active_recommendation_live=True)
    assert turn.mode == "recommendation_followup"
    assert turn.requested_new_plan is True


def test_explain_new_rec_blocked_differs_from_status_followup() -> None:
    row = {
        "id": "rec-1",
        "direction": "sell",
        "entry": 2400.0,
        "stop_loss": 2415.0,
        "targets": [2380.0],
        "status": "in_trade",
        "confidence": 0.7,
        "summary": "Sell plan",
        "interval": "15m",
    }
    blocked = explain_new_rec_blocked(row, operator_text="لا بدي توصية جديده", live_price=2390.0)
    status = grade_live_recommendation(row, operator_text="حالة التوصية", live_price=2390.0)
    assert blocked.summary != status.summary
    assert "لا يمكن إصدار توصية جديدة" in blocked.summary
    assert "نواة التداول" in blocked.summary


def test_finalize_live_plan_when_tp1_reached(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    from nanobot.trading.recommendations.store import store_recommendation, update_recommendation_status
    from nanobot.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="Sell plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=2400.0,
            stop_loss=2415.0,
            targets=[2380.0],
            interval="15m",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    rec_id = store_recommendation(decision, [], market, session_key="ws:test")
    assert rec_id
    update_recommendation_status(rec_id, "in_trade")
    row = {
        "id": rec_id,
        "direction": "sell",
        "entry": 2400.0,
        "stop_loss": 2415.0,
        "targets": [2380.0],
        "status": "in_trade",
    }
    assert finalize_live_plan_if_closed(row, live_price=2375.0) is None


@pytest.mark.asyncio
async def test_explicit_new_rec_after_tp1_runs_analysis(monkeypatch, tmp_path) -> None:
    from tests.trading.evidence_stubs import install_evidence_stubs

    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    monkeypatch.setenv("OANDA_API_TOKEN", "test-token")
    install_evidence_stubs(monkeypatch)

    from nanobot.trading.recommendations.store import latest_live_recommendation, store_recommendation
    from nanobot.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="Sell plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=2400.0,
            stop_loss=2415.0,
            targets=[2380.0],
            interval="15m",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    session_key = "websocket:ws-tp1"
    rec_id = store_recommendation(decision, [], market, session_key=session_key)
    assert rec_id
    from nanobot.trading.recommendations.store import update_recommendation_status

    update_recommendation_status(rec_id, "in_trade")
    live = latest_live_recommendation(session_key)
    assert live is not None
    assert finalize_live_plan_if_closed({**live, "targets": [2380.0]}, live_price=2375.0) is None
    assert latest_live_recommendation(session_key) is None

    turn = plan_turn("اعطيني توصية جديدة", active_recommendation_live=False)
    assert turn.mode == "full_analysis"
