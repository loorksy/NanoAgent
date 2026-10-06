import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.agent.tools.trading_team import RunTradingTeamTool
from mokli.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult


@pytest.mark.asyncio
async def test_live_plan_skips_the_team_tool(tmp_path, monkeypatch) -> None:
    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.turn_session import TurnSession, turn_session_scope
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        FinalDecisionResult,
        MarketSync,
    )

    session_key = "websocket:team-tool-live"
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    store_recommendation(
        FinalDecisionResult(
            decision="sell",
            confidence=0.7,
            summary="live sell",
            key_reasons=[],
            risk_warnings=[],
            recommendation=AgentRecommendation(
                action="sell",
                entry=2400,
                stop_loss=2415,
                targets=[2380],
            ),
        ),
        [],
        AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=[],
            last_close=2402.0,
            atr=8.0,
            sync=MarketSync(ok=True),
        ),
        session_key=session_key,
    )
    calls = {"swarm": 0, "resolve": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        return {"team_briefing": "no"}

    def _resolve(*_args, **_kwargs):
        calls["resolve"] += 1
        return type("Q", (), {"mid": 2402.0})(), "metaapi"

    monkeypatch.setattr("mokli.agent.tools.trading_team.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    tool = RunTradingTeamTool(bus=MagicMock(), subagent_manager=MagicMock())
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key=session_key)
    with request_context(ctx), turn_session_scope(TurnSession()):
        payload = json.loads(await tool.execute(preset="gold_analysis_committee"))
    assert payload["reason_key"] == "trading.live_plan_active"
    assert calls == {"swarm": 0, "resolve": 1}


@pytest.mark.asyncio
async def test_run_trading_team_executes_swarm() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    tool = RunTradingTeamTool(bus=bus, subagent_manager=MagicMock())
    ctx = RequestContext(channel="websocket", chat_id="chat-1")
    fake_final = AgentFinalResult(
        decision=FinalDecisionResult(
            decision="wait",
            confidence=0.5,
            summary="Team run",
            key_reasons=[],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait"),
        ),
        team_mode="swarm:gold_analysis_committee",
        team_agents=[{"agentId": "macro_analyst", "role": "Macro", "status": "done"}],
    )

    with request_context(ctx):
        with patch(
            "mokli.agent.tools.trading_team.run_swarm",
            new_callable=AsyncMock,
            return_value={"final": fake_final, "task_summaries": {"task-macro": "ok"}},
        ):
            raw = await tool.execute(preset="gold_analysis_committee")
    payload = json.loads(raw)
    assert payload["preset"] == "gold_analysis_committee"
    assert payload["final"]["decision"] == "wait"


@pytest.mark.asyncio
async def test_team_decision_is_not_analyzed_again(monkeypatch) -> None:
    """The team tool already ran the kernel. A later kernel call must not run it again."""
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"swarm": 0, "kernel": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        return {"team_briefing": "noted"}

    async def fake_kernel(**_kwargs):
        calls["kernel"] += 1
        return object()

    monkeypatch.setattr("mokli.agent.tools.trading_team.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.trading.kernel.run_trading_kernel", fake_kernel)
    monkeypatch.setattr("mokli.agent.tools.trading_kernel.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_team.result_to_wire",
        lambda _result: {"decision": "wait", "summary": "once"},
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel.result_to_wire",
        lambda _result: {"decision": "wait", "summary": "once"},
    )
    team = RunTradingTeamTool(bus=MagicMock(), subagent_manager=None)
    kernel = RunTradingKernelTool(bus=MagicMock(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1")
    with request_context(ctx), turn_session_scope(TurnSession()):
        first = json.loads(await team.execute(preset="gold_analysis_committee"))
        again = json.loads(await kernel.execute())
        other = json.loads(await team.execute(preset="gold_mtf_panel"))
        replaced = json.loads(await kernel.execute(force_new_plan=True))
    assert first["final"]["decision"] == "wait"
    assert again["decision"] == "wait"
    assert other["preset"] == "gold_mtf_panel"
    assert other["final"]["decision"] == "wait"
    assert replaced["decision"] == "wait"
    assert calls == {"swarm": 1, "kernel": 2}
    print(f"KERNEL_REPEAT swarm={calls['swarm']} kernel={calls['kernel'] - 1}")
    assert "Do not call run_trading_kernel again" in team.description
    assert "Do not call run_trading_team first" in kernel.parameters["properties"]["decision_review"]["description"]
