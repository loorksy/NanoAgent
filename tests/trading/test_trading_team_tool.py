import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.agent.tools.trading_team import RunTradingTeamTool
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult


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
            "nanobot.agent.tools.trading_team.run_swarm",
            new_callable=AsyncMock,
            return_value={"final": fake_final, "task_summaries": {"task-macro": "ok"}},
        ):
            raw = await tool.execute(preset="gold_analysis_committee")
    payload = json.loads(raw)
    assert payload["preset"] == "gold_analysis_committee"
    assert payload["final"]["decision"] == "wait"
