"""Tests for gold trading agent tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.agent.tools.trading_chart import AnalyzeGoldTool, GetGoldQuoteTool
from nanobot.trading.stage_events import emit_stage
from nanobot.trading.stage_delivery import TradingStagePublisher


@pytest.mark.asyncio
async def test_get_gold_quote_unconfigured() -> None:
    tool = GetGoldQuoteTool.create(MagicMock())
    with patch("nanobot.agent.tools.trading_chart.load_trading_config") as cfg:
        cfg.return_value = MagicMock(oanda_configured=False)
        result = await tool.execute()
    assert "not configured" in result.lower()


@pytest.mark.asyncio
async def test_analyze_gold_publishes_result() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = AnalyzeGoldTool(bus=bus)
    ctx = RequestContext(channel="websocket", chat_id="chat-1")
    fake_result = MagicMock()
    fake_result.decision = MagicMock(
        decision="wait",
        confidence=0.5,
        summary="No trade",
        key_reasons=[],
        risk_warnings=[],
        gate_chain=None,
        refusal_summary=None,
        recommendation=MagicMock(
            action="wait",
            entry=None,
            stop_loss=None,
            targets=[],
            interval="15m",
        ),
        plan_type=None,
        execution_state=None,
    )
    fake_result.recommendation_id = None
    fake_result.cards = []
    fake_result.stages = []
    fake_result.team_mode = "core"
    fake_result.drawings = []

    with request_context(ctx):
        with patch(
            "nanobot.agent.tools.trading_chart.run_unified_chart_agent",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            raw = await tool.execute(interval="15m")
    payload = json.loads(raw)
    assert payload["decision"] == "wait"
    assert bus.publish_outbound.await_count >= 2


def test_stage_publisher_sync_emit_schedules_task() -> None:
    publisher = TradingStagePublisher(None, channel="websocket", chat_id="x")
    event = emit_stage("market_data", "running")
    # No bus — should not raise
    publisher.sync_emit(event)
