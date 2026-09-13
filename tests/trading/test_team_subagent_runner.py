from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.trading.teams.subagent_runner import TeamRunCollector, run_team_role
from nanobot.utils.llm_runtime import LLMRuntime


@pytest.mark.asyncio
async def test_run_team_role_uses_llm_fallback() -> None:
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="Liquidity favors buy-side sweep."))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    collector = TeamRunCollector()

    with request_context(RequestContext(channel="websocket", chat_id="1", runtime=runtime)):
        summary = await run_team_role(
            agent_id="liquidity_analyst",
            role="Liquidity Analyst",
            task_text="Map equal highs and lows.",
            evidence_text='{"symbol":"XAUUSD","last_close":2650}',
            collector=collector,
        )

    assert "Liquidity" in summary
    assert len(collector.agents) >= 1
    assert collector.agents[-1]["status"] == "done"
