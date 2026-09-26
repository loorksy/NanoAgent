"""Agent-controlled trading UI delivery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.agent.tools.trading_chart import (
    AnalyzeGoldTool,
    GetGoldQuoteTool,
    GetLiveRecommendationTool,
)
from mokli.trading.tool_delivery import should_publish_trading_ui


def test_should_publish_trading_ui_requires_opt_in() -> None:
    assert should_publish_trading_ui(False) is False
    assert should_publish_trading_ui(True) is True


def _quote_payload() -> dict:
    return {
        "aborted": False,
        "nodes": {
            "market_data": {
                "quote_bid": 4332.0,
                "quote_ask": 4333.0,
                "quote_mid": 4332.5,
                "tradeable": True,
            }
        },
        "display": {"bid": "4332.00", "ask": "4333.00", "mid": "4332.50"},
    }


@pytest.mark.asyncio
async def test_get_gold_quote_does_not_publish_by_default() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = GetGoldQuoteTool(bus=bus)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    with request_context(ctx):
        with patch("mokli.agent.tools.trading_chart.load_trading_config") as cfg:
            cfg.return_value = MagicMock(oanda_configured=True)
            with patch(
                "mokli.agent.tools.trading_chart.fetch_evidence_nodes",
                new_callable=AsyncMock,
                return_value=_quote_payload(),
            ):
                raw = await tool.execute()
    payload = json.loads(raw)
    assert payload["mid"] == 4332.5
    assert payload["display"]["mid"] == "4332.50"
    assert payload["artifacts"] == []
    bus.publish_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_get_gold_quote_publishes_when_present_ui() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = GetGoldQuoteTool(bus=bus)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    with request_context(ctx):
        with patch("mokli.agent.tools.trading_chart.load_trading_config") as cfg:
            cfg.return_value = MagicMock(oanda_configured=True)
            with patch(
                "mokli.agent.tools.trading_chart.fetch_evidence_nodes",
                new_callable=AsyncMock,
                return_value=_quote_payload(),
            ):
                await tool.execute(present_ui=True)
    assert bus.publish_outbound.await_count >= 1


@pytest.mark.asyncio
async def test_analyze_gold_returns_live_plan_error_instead_of_second_plan() -> None:
    from mokli.trading.kernel import LivePlanActive

    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = AnalyzeGoldTool(bus=bus, subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")

    async def _kernel(**_kwargs):
        raise LivePlanActive({"id": "rec-1", "direction": "sell"})

    with request_context(ctx):
        with patch("mokli.agent.tools.trading_chart.run_trading_kernel", _kernel):
            result = await tool.execute()
    payload = json.loads(str(result))
    assert payload["ok"] is False
    assert payload["reason_key"] == "trading.live_plan_active"
    assert payload["live_plan"]["id"] == "rec-1"
    assert "get_live_recommendation" in payload["instruction"]
    bus.publish_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_get_live_recommendation_returns_plan_and_price() -> None:
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
            "mokli.agent.tools.trading_chart.sync_session_live_plan",
            return_value=live_row,
        ):
            with patch("mokli.agent.tools.trading_chart.load_trading_config") as cfg:
                cfg.return_value = MagicMock(oanda_configured=True)
                with patch("mokli.agent.tools.trading_chart.fetch_quote", return_value=quote):
                    with patch(
                        "mokli.agent.tools.trading_chart.grade_outcome_status",
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
