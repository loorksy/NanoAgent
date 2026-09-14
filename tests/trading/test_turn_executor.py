"""Tests for Phase J light-path turn executor."""

import asyncio

import pytest

from nanobot.trading.config import load_trading_config
from nanobot.trading.policy_guard import validate_turn_plan
from nanobot.trading.turn_executor import execute_light_path
from nanobot.trading.turn_planner import plan_turn


def test_plan_turn_chart_capture_declares_visual_capture_node() -> None:
    turn = plan_turn("أرسل صورة شارت الذهب")
    assert turn.mode == "chart_capture"
    assert turn.nodes == ("visual_capture",)


def test_plan_turn_followup_declares_market_data_node() -> None:
    turn = plan_turn("اعطيني توصية", active_recommendation_live=True)
    assert turn.mode == "recommendation_followup"
    assert turn.nodes == ("market_data",)


def test_light_path_never_shadow_expands_to_full_graph() -> None:
    turn = plan_turn("كم سعر الذهب؟")
    validated = validate_turn_plan(turn, shadow_mode=True)
    assert validated.executed_nodes == ("market_data",)
    assert validated.executed_graph.layers == (("market_data",),)


@pytest.mark.asyncio
async def test_execute_light_path_price_no_live_quote(monkeypatch) -> None:
    from tests.trading.evidence_stubs import install_evidence_stubs

    monkeypatch.setenv("OANDA_API_TOKEN", "test-token")
    stubs = install_evidence_stubs(monkeypatch, gate_allowed=False)
    stubs["market"].quote_mid = None
    stubs["market"].quote_bid = None
    stubs["market"].quote_ask = None
    stubs["market"].last_close = 2400.0

    turn = plan_turn("كم سعر الذهب؟")
    result = await execute_light_path(
        turn,
        text="كم سعر الذهب؟",
        channel="websocket",
        chat_id="ws:1",
        bus=None,
    )
    assert result is not None
    assert "لا يوجد سعر حي" in result.content or "No live quote" in result.content


@pytest.mark.asyncio
async def test_execute_light_path_price(monkeypatch) -> None:
    from tests.trading.evidence_stubs import install_evidence_stubs

    monkeypatch.setenv("OANDA_API_TOKEN", "test-token")
    install_evidence_stubs(monkeypatch, gate_allowed=False)
    turn = plan_turn("كم سعر الذهب؟")
    result = await execute_light_path(
        turn,
        text="كم سعر الذهب؟",
        channel="websocket",
        chat_id="ws:1",
        bus=None,
    )
    assert result is not None
    assert "2400" in result.content


@pytest.mark.asyncio
async def test_execute_light_path_followup_uses_market_data(monkeypatch) -> None:
    from tests.trading.evidence_stubs import install_evidence_stubs

    install_evidence_stubs(monkeypatch, gate_allowed=False)
    live = {
        "id": "rec-1",
        "direction": "buy",
        "entry": 2400.0,
        "stop_loss": 2385.0,
        "targets": [2420.0],
        "status": "waiting",
        "confidence": 0.7,
        "summary": "Buy plan",
        "interval": "15m",
    }
    turn = plan_turn("اعطيني توصية", active_recommendation_live=True)
    result = await execute_light_path(
        turn,
        text="اعطيني توصية",
        channel="websocket",
        chat_id="ws:1",
        live=live,
    )
    assert result is not None
    assert result.content


def test_fast_path_price_still_works_without_oanda(monkeypatch) -> None:
    monkeypatch.delenv("OANDA_API_TOKEN", raising=False)
    result = asyncio.run(
        execute_light_path(
            plan_turn("gold price"),
            text="gold price",
            channel="websocket",
            chat_id="ws:1",
        )
    )
    assert result is not None
    assert "Market data" in result.content or "بيانات السوق" in result.content
