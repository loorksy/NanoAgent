import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.trading.teams.evidence_text import scope_market_evidence
from mokli.trading.teams.subagent_runner import TeamRunCollector, run_team_role
from mokli.utils.llm_runtime import LLMRuntime


def test_non_structure_roles_do_not_receive_the_candle_dump() -> None:
    candles = [{"t": index, "o": 1, "h": 2, "l": 0, "c": 1} for index in range(40)]
    full = json.dumps({"symbol": "XAUUSD", "last_close": 2300, "candles": candles})
    technical = scope_market_evidence(full, "Technical Analyst", "role:structure")
    risk = scope_market_evidence(full, "Risk Officer", "role:risk")
    macro = scope_market_evidence(full, "Macro News Analyst", "role:macro")
    assert "candles" in technical
    assert "candles" not in risk
    assert "candles" not in macro
    assert "2300" in risk
    assert len(risk) < len(full) // 2


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


@pytest.mark.asyncio
async def test_run_team_role_publishes_only_roles_that_run() -> None:
    from mokli.agent_api.events import translate_runtime_event
    from mokli.events import TeamRoleEvent

    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="STANCE: wait"))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    bus = MagicMock()
    bus.publish = AsyncMock()

    with request_context(
        RequestContext(
            channel="agent_api",
            chat_id="chat",
            session_key="agent_api:chat",
            runtime=runtime,
        )
    ):
        await run_team_role(
            agent_id="risk",
            role="Risk Officer",
            task_text="Name blocking risks.",
            evidence_text="{}",
            bus=bus,
        )

    events = [call.args[0] for call in bus.publish.await_args_list]
    assert [event.status for event in events] == ["running", "done"]
    assert all(isinstance(event, TeamRoleEvent) for event in events)
    assert events[0].session_key == "agent_api:chat"
    assert events[0].role == "Risk Officer"
    started = translate_runtime_event(events[0])
    finished = translate_runtime_event(events[1])
    assert started is not None and started["kind"] == "subagent"
    assert started["session"] == "chat"
    assert started["data"]["event"] == "started"
    assert finished is not None and finished["data"]["event"] == "finished"
    assert finished["data"]["id"] == "risk"

    provider.chat = AsyncMock(side_effect=RuntimeError("down"))
    bus.publish.reset_mock()
    with request_context(
        RequestContext(
            channel="agent_api",
            chat_id="chat",
            session_key="agent_api:chat",
            runtime=runtime,
        )
    ):
        failed = await run_team_role(
            agent_id="macro",
            role="Macro News Analyst",
            task_text="News only.",
            evidence_text="{}",
            bus=bus,
        )
    failed_events = [call.args[0] for call in bus.publish.await_args_list]
    assert [event.status for event in failed_events] == ["running", "failed"]
    assert "Macro News Analyst" in failed

    quiet = MagicMock()
    quiet.publish = AsyncMock()
    with request_context(RequestContext(channel="websocket", chat_id="1", runtime=runtime)):
        await run_team_role(
            agent_id="trend",
            role="Trend Analyst",
            task_text="Trend only.",
            evidence_text="{}",
            bus=quiet,
        )
    quiet.publish.assert_not_awaited()
