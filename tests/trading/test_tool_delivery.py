"""Agent-controlled trading UI delivery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.agent.tools.trading_chart import (
    AnalyzeGoldTool,
    GetGoldQuoteTool,
    GetLiveRecommendationTool,
)
from nanobot.trading.tool_delivery import should_publish_trading_ui


def test_should_publish_trading_ui_agent_first_requires_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "true")
    assert should_publish_trading_ui(False) is False
    assert should_publish_trading_ui(True) is True


def test_should_publish_trading_ui_legacy_always_publishes(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "false")
    assert should_publish_trading_ui(False) is True
    assert should_publish_trading_ui(True) is True


@pytest.mark.asyncio
async def test_get_gold_quote_does_not_publish_by_default(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "true")
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = GetGoldQuoteTool(bus=bus)
    quote = MagicMock(symbol="XAUUSD", bid=4332.0, ask=4333.0, mid=4332.5, tradeable=True)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    with request_context(ctx):
        with patch("nanobot.agent.tools.trading_chart.load_trading_config") as cfg:
            cfg.return_value = MagicMock(oanda_configured=True)
            with patch("nanobot.agent.tools.trading_chart.fetch_quote", return_value=quote):
                raw = await tool.execute()
    payload = json.loads(raw)
    assert payload["mid"] == 4332.5
    bus.publish_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_get_gold_quote_publishes_when_present_ui(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "true")
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = GetGoldQuoteTool(bus=bus)
    quote = MagicMock(symbol="XAUUSD", bid=4332.0, ask=4333.0, mid=4332.5, tradeable=True)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    with request_context(ctx):
        with patch("nanobot.agent.tools.trading_chart.load_trading_config") as cfg:
            cfg.return_value = MagicMock(oanda_configured=True)
            with patch("nanobot.agent.tools.trading_chart.fetch_quote", return_value=quote):
                await tool.execute(present_ui=True)
    assert bus.publish_outbound.await_count >= 1


@pytest.mark.asyncio
async def test_analyze_gold_blocks_live_plan_followup_in_agent_first(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "true")
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = AnalyzeGoldTool(bus=bus, subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    with request_context(ctx):
        with patch(
            "nanobot.agent.tools.trading_chart.latest_live_recommendation",
            return_value={"id": "rec-1", "direction": "sell"},
        ):
            result = await tool.execute()
    assert "get_live_recommendation" in result.lower()
    bus.publish_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_get_live_recommendation_returns_plan_and_price(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "true")
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = GetLiveRecommendationTool(bus=bus)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")
    live_row = {
        "id": "rec-1",
        "direction": "sell",
        "entry": 3349.42,
        "stop_loss": 3360.0,
        "targets": [3336.81, 3324.21],
        "status": "in_trade",
        "summary": "Sell gold",
        "confidence": 0.7,
        "interval": "15m",
    }
    quote = MagicMock(symbol="XAUUSD", bid=4332.0, ask=4333.0, mid=4332.5, tradeable=True)

    with request_context(ctx):
        with patch(
            "nanobot.agent.tools.trading_chart.latest_live_recommendation",
            return_value=live_row,
        ):
            with patch("nanobot.agent.tools.trading_chart.load_trading_config") as cfg:
                cfg.return_value = MagicMock(oanda_configured=True)
                with patch("nanobot.agent.tools.trading_chart.fetch_quote", return_value=quote):
                    with patch(
                        "nanobot.agent.tools.trading_chart.grade_outcome_status",
                        return_value="in_trade",
                    ):
                        raw = await tool.execute()
    payload = json.loads(raw)
    assert payload["has_live_plan"] is True
    assert payload["live_price"] == 4332.5
    assert payload["plan"]["entry"] == 3349.42
    assert payload["display"]["live_price"] == "4332.50"
    assert payload["display"]["entry"] == "3349.42"
    bus.publish_outbound.assert_not_called()
