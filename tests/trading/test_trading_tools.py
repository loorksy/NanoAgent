"""Tests for gold trading agent tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.agent.tools.trading_chart import AnalyzeGoldTool, GetGoldQuoteTool
from mokli.trading.stage_delivery import TradingStagePublisher
from mokli.trading.stage_events import emit_stage


@pytest.mark.asyncio
async def test_get_gold_quote_unconfigured() -> None:
    tool = GetGoldQuoteTool.create(MagicMock())
    with patch("mokli.agent.tools.trading_chart.load_trading_config") as cfg:
        cfg.return_value = MagicMock(oanda_configured=False)
        result = await tool.execute()
    payload = json.loads(str(result))
    assert payload["ok"] is False
    assert payload["reason_key"] == "trading.market_feed_unconfigured"


@pytest.mark.asyncio
async def test_analyze_gold_publishes_result_when_present_ui() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = AnalyzeGoldTool(bus=bus, subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")
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
    fake_result.team_agents = []
    fake_result.drawings = []
    image = "data:image/png;base64," + ("A" * 4000)
    fake_result.visual_snapshots = [{"timeframe": "15m", "image": image}]

    with request_context(ctx):
        with patch(
            "mokli.agent.tools.trading_chart.run_trading_kernel",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            raw = await tool.execute(interval="15m", present_ui=True)
    payload = json.loads(raw)
    assert payload["decision"] == "wait"
    assert "data:image" not in raw
    assert "chartSnapshots" not in payload
    published = json.dumps(
        [call.args[0].metadata for call in bus.publish_outbound.await_args_list],
        default=str,
    )
    assert image in published
    assert bus.publish_outbound.await_count >= 2


@pytest.mark.asyncio
async def test_analyze_gold_reuses_the_turn_decision(monkeypatch) -> None:
    """A recommendation already made this turn is not analyzed again."""
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"kernel": 0}

    async def fake_kernel(**_kwargs):
        calls["kernel"] += 1
        return object()

    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.result_to_wire",
        lambda _result: {"decision": "wait", "summary": "stored"},
    )
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = AnalyzeGoldTool(bus=bus, subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:chat-1")
    stored = MagicMock()
    turn = TurnSession()
    turn.decision_wire = json.dumps({"decision": "wait", "summary": "stored"})
    turn.kernel_result = stored
    with request_context(ctx), turn_session_scope(turn):
        raw = await tool.execute(present_ui=True)
        replaced = await tool.execute(force_new_plan=True)
    assert json.loads(raw)["decision"] == "wait"
    assert json.loads(replaced)["summary"] == "stored"
    assert calls["kernel"] == 1
    assert bus.publish_outbound.await_count >= 1
    print(f"ANALYZE_REPEAT kernel={calls['kernel'] - 1}")


def test_stage_publisher_sync_emit_schedules_task() -> None:
    publisher = TradingStagePublisher(None, channel="websocket", chat_id="x")
    event = emit_stage("market_data", "running")
    # No bus — should not raise
    publisher.sync_emit(event)
