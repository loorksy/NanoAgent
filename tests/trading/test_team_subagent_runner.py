import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.trading.teams.evidence_text import scope_market_evidence
from mokli.trading.teams.subagent_runner import TeamRunCollector, run_team_role
from mokli.utils.llm_runtime import LLMRuntime


@pytest.mark.asyncio
async def test_team_role_with_runtime_does_not_open_a_tool_loop() -> None:
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="levels hold\nSTANCE: wait"))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    manager = MagicMock()
    manager.run_inline = AsyncMock(return_value="should not run")

    with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
        summary = await run_team_role(
            agent_id="risk",
            role="Risk Officer",
            task_text="Name blocking risks.",
            evidence_text='{"last_close": 2300}',
            system_prompt="role:risk",
            manager=manager,
        )

    manager.run_inline.assert_not_awaited()
    provider.chat.assert_awaited()
    kwargs = provider.chat.await_args.kwargs
    assert "tools" not in kwargs
    assert kwargs["max_tokens"] == 1024
    messages = kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "STANCE: wait" in messages[0]["content"]
    assert "2300" in messages[1]["content"]
    assert "Name blocking risks." in messages[1]["content"]
    assert summary.startswith("levels hold")


@pytest.mark.asyncio
async def test_role_prompt_receives_valid_evidence_json() -> None:
    candles = [
        {"t": index, "o": 2300.0, "h": 2301.0, "l": 2299.0, "c": 2300.5}
        for index in range(400)
    ]
    evidence = json.dumps({"symbol": "XAUUSD", "last_close": 2300.5, "candles": candles})
    assert len(evidence) > 12000
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="STANCE: wait"))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)

    with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
        await run_team_role(
            agent_id="technical",
            role="Technical Analyst",
            task_text="Read the structure.",
            evidence_text=evidence,
            system_prompt="role:structure",
        )

    user = provider.chat.await_args.kwargs["messages"][1]["content"]
    blob = user.split("FROZEN MARKET EVIDENCE", 1)[1].split("\n", 1)[1]
    parsed = json.loads(blob)
    assert parsed["last_close"] == 2300.5
    assert parsed["candles"][-1]["t"] == 399
    assert len(parsed["candles"]) < 400


@pytest.mark.asyncio
async def test_published_role_summary_keeps_a_trailing_stance() -> None:
    from mokli.trading.result_wire import result_to_wire
    from mokli.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult

    body = "level " * 800
    text = f"{body}\nSTANCE: sell"
    assert "STANCE: sell" not in text[:2000]
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content=text))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    collector = TeamRunCollector()

    with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
        summary = await run_team_role(
            agent_id="technical",
            role="Technical Analyst",
            task_text="Read the structure.",
            evidence_text='{"last_close": 2300}',
            system_prompt="role:structure",
            collector=collector,
        )

    assert summary == text
    published = collector.agents[0]["summary"]
    assert published.endswith("STANCE: sell")
    assert collector.agents[0]["display"] == "اكتملت مراجعة الهيكل"
    assert len(published) < len(text)
    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.5,
        summary="sell",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="sell"),
    )
    wire = result_to_wire(
        AgentFinalResult(
            decision=decision,
            team_agents=[
                {"status": "done", "summary": published},
                {"status": "done", "summary": "flow supports it\nSTANCE: sell"},
            ],
        )
    )
    assert wire["agreement"] == {"stance": "sell", "agreeing": 2, "votes": 2}


def test_upstream_brief_keeps_the_stance_and_drops_the_rest() -> None:
    from mokli.trading.teams.runtime import brief_for_upstream

    body = "level " * 800
    summary = f"{body}\nSTANCE: sell"
    brief = brief_for_upstream(summary)
    assert len(brief) < len(summary) // 5
    assert brief.endswith("STANCE: sell")
    assert "STANCE: sell" not in brief[:400]


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


def test_long_candle_evidence_stays_valid_json() -> None:
    from mokli.trading.teams.evidence_text import fit_evidence_text

    candles = [
        {
            "t": 1_700_000_000_000 + index,
            "o": 2300.0,
            "h": 2302.0,
            "l": 2298.0,
            "c": 2301.0 + index,
        }
        for index in range(400)
    ]
    payload = {
        "symbol": "XAUUSD",
        "interval": "15m",
        "last_close": candles[-1]["c"],
        "atr": 2.5,
        "quote_mid": candles[-1]["c"],
        "sync_ok": True,
        "candles": candles,
    }
    raw = json.dumps(payload, ensure_ascii=False)
    assert len(raw) > 12000
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw[:12000])

    fitted = fit_evidence_text(raw)
    parsed = json.loads(fitted)
    assert len(fitted) <= 12000
    assert parsed["symbol"] == "XAUUSD"
    assert parsed["last_close"] == candles[-1]["c"]
    assert parsed["candles"][-1] == candles[-1]
    assert len(parsed["candles"]) < len(candles)
    short = json.dumps({"last_close": 2300})
    assert fit_evidence_text(short) == short


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
