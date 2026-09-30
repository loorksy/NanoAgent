import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mokli.agent.tools.context import RequestContext, request_context
from mokli.trading.teams.evidence_text import (
    compact_timeframe_window,
    named_chart_interval,
    scope_market_evidence,
    trend_evidence,
)
from mokli.trading.teams.subagent_runner import TeamRunCollector, run_team_role
from mokli.trading.types import AgentMarketContext, Candle, MarketSync
from mokli.utils.helpers import estimate_prompt_tokens
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
    user = kwargs["messages"][1]["content"]
    assert "upstream note" in user


@pytest.mark.asyncio
async def test_upstream_note_prices_are_allowed_beside_the_quote() -> None:
    """A level in the prior brief is not an invented price outside the quote JSON."""
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="noted\nSTANCE: wait"))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)

    with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
        await run_team_role(
            agent_id="bull",
            role="Bull Advocate",
            task_text="Build the bull case.\ntechnical: swing high 2310\nSTANCE: buy",
            evidence_text='{"symbol": "XAUUSD", "quote_mid": 2300}',
            system_prompt="role:bull",
        )

    user = provider.chat.await_args.kwargs["messages"][1]["content"]
    system = provider.chat.await_args.kwargs["messages"][0]["content"]
    assert "swing high 2310" in user
    assert "upstream note" in user
    assert "upstream note" in system
    assert "2310" not in user.split("FROZEN MARKET EVIDENCE", 1)[1]


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


@pytest.mark.asyncio
async def test_cancelled_team_role_closes_the_row(monkeypatch) -> None:
    from mokli.events import TeamRoleEvent
    from mokli.trading.teams import subagent_runner as runner_mod
    from mokli.trading.teams.role_display import role_phrase

    clock = {"now": 10.0}
    monkeypatch.setattr(runner_mod.time, "time", lambda: clock["now"])
    entered = asyncio.Event()

    async def slow_chat(*_args: object, **_kwargs: object) -> MagicMock:
        clock["now"] = 13.7
        entered.set()
        await asyncio.sleep(30)
        return MagicMock(content="late")

    provider = MagicMock()
    provider.chat = slow_chat
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    bus = MagicMock()
    bus.publish = AsyncMock()
    collector = TeamRunCollector()

    async def _run() -> str:
        with request_context(
            RequestContext(
                channel="agent_api",
                chat_id="chat",
                session_key="agent_api:chat",
                runtime=runtime,
            )
        ):
            return await run_team_role(
                agent_id="risk",
                role="Risk Officer",
                task_text="Name blocking risks.",
                evidence_text="{}",
                bus=bus,
                collector=collector,
            )

    task = asyncio.create_task(_run())
    await asyncio.wait_for(entered.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    events = [call.args[0] for call in bus.publish.await_args_list]
    assert [event.status for event in events] == ["running", "failed"]
    assert all(isinstance(event, TeamRoleEvent) for event in events)
    assert events[1].duration_ms == 3700
    assert events[1].summary == "cancelled"
    assert events[1].display == role_phrase("Risk Officer", "failed")
    assert collector.agents[-1]["status"] == "failed"
    assert collector.agents[-1]["durationMs"] == 3700


def _candle(time_ms: int, close: float) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1,
        complete=True,
    )


def _market(interval: str, time_ms: int, close: float) -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval=interval,
        candles=[_candle(time_ms, close)],
        last_close=close,
        atr=2.5,
        sync=MarketSync(ok=True),
        quote_mid=close,
    )


def test_trend_role_does_not_reread_the_lead_candles() -> None:
    candles = [
        {
            "t": 1_700_000_000_000 + index,
            "o": 2300.0,
            "h": 2302.0,
            "l": 2298.0,
            "c": 2301.0,
        }
        for index in range(40)
    ]
    lead = json.dumps(
        {
            "symbol": "XAUUSD",
            "interval": "15m",
            "last_close": 2301.0,
            "atr": 2.5,
            "quote_mid": 2301.0,
            "sync_ok": True,
            "candles": candles,
        },
        ensure_ascii=False,
    )
    windows = [
        compact_timeframe_window(_market(interval, 10 + offset, 2400.0 + offset))
        for offset, interval in enumerate(("1h", "4h", "1d"))
    ]
    scoped = trend_evidence(lead, windows)
    parsed = json.loads(scoped)
    assert "candles" not in parsed
    assert parsed["quote_mid"] == 2301.0
    assert [row["interval"] for row in parsed["higher_timeframes"]] == ["1h", "4h", "1d"]
    assert "2302.0" not in scoped
    before = estimate_prompt_tokens([{"role": "user", "content": lead}])
    after = estimate_prompt_tokens([{"role": "user", "content": scoped}])
    assert after < before
    assert named_chart_interval("Trend Analyst") is None
    assert named_chart_interval("H1 Analyst") == "1h"
    assert named_chart_interval("H4 Analyst") == "4h"
    assert named_chart_interval("D1 Analyst") == "1d"
    synth = scope_market_evidence(lead, "MTF Synthesizer", "role:mtf_synthesizer")
    assert "candles" not in json.loads(synth)
    print(f"TOKEN_TREND_EVIDENCE before={before} after={after}")


@pytest.mark.asyncio
async def test_named_timeframe_roles_load_their_own_candles(monkeypatch) -> None:
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str]] = []
    loads: list[tuple[str, int]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((str(kwargs.get("role")), str(kwargs.get("evidence_text"))))
        return "STANCE: wait"

    quote_flags: list[bool] = []

    def fake_context(
        symbol: str = "XAUUSD",
        interval: str = "15m",
        limit: int = 240,
        *,
        include_quote: bool = True,
    ):
        del symbol
        quote_flags.append(include_quote)
        loads.append((interval, limit))
        closes = {"1h": 2310.0, "4h": 2320.0, "1d": 2330.0}
        stamps = {"1h": 1, "4h": 2, "1d": 3}
        return _market(interval, stamps[interval], closes[interval])

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr("mokli.trading.teams.runtime.run_market_data_agent", lambda *_a, **_k: _market("15m", 111, 2300.0))
    monkeypatch.setattr("mokli.trading.teams.runtime.build_agent_market_context", fake_context)

    async def search(query: str) -> str:
        del query
        return "DXY steady"

    panel = await run_swarm(
        "gold_mtf_panel",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = dict(seen)
    h1 = json.loads(by_role["H1 Analyst"])
    h4 = json.loads(by_role["H4 Analyst"])
    d1 = json.loads(by_role["D1 Analyst"])
    synth = json.loads(by_role["MTF Synthesizer"])
    assert h1["interval"] == "1h" and h1["candles"][0]["t"] == 1
    assert h4["interval"] == "4h" and h4["candles"][0]["t"] == 2
    assert d1["interval"] == "1d" and d1["candles"][0]["t"] == 3
    assert "candles" not in synth
    assert all(limit == 120 for _interval, limit in loads)
    assert quote_flags == [True, True, True]
    assert panel["final"] is None

    seen.clear()
    loads.clear()
    quote_flags.clear()
    review = await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = dict(seen)
    technical = json.loads(by_role["Technical Analyst"])
    trend = json.loads(by_role["Trend Analyst"])
    macro = json.loads(by_role["Macro News Analyst"])
    risk = json.loads(by_role["Risk Officer"])
    assert technical["candles"][0]["t"] == 111
    assert "macroDrivers" not in technical
    assert "candles" not in trend
    assert "macroDrivers" not in trend
    assert "candles" not in macro
    assert isinstance(macro["macroDrivers"], list)
    assert macro["macroDrivers"]
    assert "macroDrivers" not in risk
    assert [row["interval"] for row in trend["higher_timeframes"]] == ["1h", "4h", "1d"]
    assert {interval for interval, _limit in loads} == {"1h", "4h", "1d"}
    assert quote_flags == [False, False, False]
    assert review["final"] is None


@pytest.mark.asyncio
async def test_trend_windows_do_not_download_a_quote(monkeypatch) -> None:
    """A trend window needs bars. Three sequential context builds used to quote each one."""
    from mokli.trading.market_context import build_agent_market_context
    from mokli.trading.oanda import OandaCandle, OandaQuote
    from mokli.trading.teams.runtime import evidence_for_team_role
    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    quotes = {"n": 0}
    candles = {"n": 0}

    def fake_candles(*_args: object, **_kwargs: object) -> tuple[list[OandaCandle], bool]:
        candles["n"] += 1
        row = OandaCandle(
            time_ms=1_700_000_000_000,
            open=2300,
            high=2302,
            low=2298,
            close=2301,
            volume=1,
            complete=True,
        )
        return [row] * 22, False

    def fake_quote(*_args: object, **_kwargs: object) -> OandaQuote:
        quotes["n"] += 1
        return OandaQuote(symbol="XAUUSD", bid=2300, ask=2302, mid=2301, tradeable=True)

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", fake_candles)
    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", fake_quote)
    lead = json.dumps(
        {"symbol": "XAUUSD", "interval": "15m", "last_close": 2301.0, "quote_mid": 2301.0},
    )

    with turn_session_scope():
        for interval in ("1h", "4h", "1d"):
            build_agent_market_context("XAUUSD", interval, 120)
        before = quotes["n"]

    quotes["n"] = 0
    candles["n"] = 0
    with turn_session_scope():
        text = await evidence_for_team_role(lead, "Trend Analyst", "role:timeframe")
    parsed = json.loads(text)
    assert "candles" not in parsed
    assert parsed["quote_mid"] == 2301.0
    assert [row["interval"] for row in parsed["higher_timeframes"]] == ["1h", "4h", "1d"]
    assert quotes["n"] == 0
    assert candles["n"] == 3
    print(f"QUOTE_TREND before={before} after={quotes['n']}")
    assert before == 3

    quotes["n"] = 0
    with turn_session_scope():
        named = await evidence_for_team_role(lead, "H1 Analyst", "role:timeframe")
    assert quotes["n"] == 1
    assert "candles" in json.loads(named)


@pytest.mark.asyncio
async def test_review_runs_only_when_stances_conflict(monkeypatch) -> None:
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import review_needed, run_swarm

    assert review_needed({"a": "STANCE: buy", "b": "STANCE: buy"}) is False
    assert review_needed({"a": "STANCE: buy", "b": "STANCE: sell"}) is True
    assert review_needed({"a": "no line"}) is False

    reset_macro_cache_for_tests()
    calls: list[str] = []
    sides = {
        "Technical Analyst": "buy",
        "Macro News Analyst": "sell",
        "Trend Analyst": "buy",
        "Risk Officer": "buy",
    }

    async def fake_team_role(**kwargs: object) -> str:
        role = str(kwargs.get("role"))
        calls.append(role)
        return f"note\nSTANCE: {sides.get(role, 'wait')}"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.build_agent_market_context",
        lambda *a, **k: _market("1h", 1, 2310.0),
    )

    async def search(query: str) -> str:
        del query
        return "DXY steady"

    conflicted = await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    assert calls.count("Review Analyst") == 1
    assert "task-review" in conflicted["task_summaries"]

    calls.clear()
    sides.update({
        "Technical Analyst": "wait",
        "Macro News Analyst": "wait",
        "Trend Analyst": "wait",
        "Risk Officer": "wait",
    })
    agreed = await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    assert "Review Analyst" not in calls
    assert "task-review" not in agreed["task_summaries"]

    calls.clear()
    sides["Macro News Analyst"] = "sell"
    await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
        max_review_rounds=0,
    )
    assert "Review Analyst" not in calls


@pytest.mark.asyncio
async def test_event_role_reads_the_driver_list(monkeypatch) -> None:
    """The event analyst ranks the driver rows. A 400-character note is not that list."""
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((
            str(kwargs.get("role")),
            str(kwargs.get("task_text")),
            str(kwargs.get("evidence_text")),
        ))
        return "events noted\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "FOMC holds, dollar firm"

    await run_swarm(
        "gold_news_war_room",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: evidence for role, _task, evidence in seen}
    news_task = next(task for role, task, _evidence in seen if role == "News Scanner")
    assert "calendar" not in news_task.lower()
    assert "headline" not in news_task.lower()
    old_task = "Scan macro calendar and headlines for XAUUSD."
    task_before = estimate_prompt_tokens([{"role": "user", "content": old_task}])
    task_after = estimate_prompt_tokens([{"role": "user", "content": news_task}])
    print(f"NEWS_TASK before={task_before} after={task_after}")
    news = json.loads(by_role["News Scanner"])
    event = json.loads(by_role["Event Analyst"])
    scenario = json.loads(by_role["Scenario Planner"])
    assert "candles" not in news
    assert "candles" not in event
    assert isinstance(news["macroDrivers"], list) and news["macroDrivers"]
    assert event["macroDrivers"] == news["macroDrivers"]
    assert "candles" in scenario
    assert "macroDrivers" not in scenario
    quote_only = {key: value for key, value in event.items() if key != "macroDrivers"}
    before = estimate_prompt_tokens([{"role": "user", "content": json.dumps(quote_only)}])
    after = estimate_prompt_tokens([{"role": "user", "content": json.dumps(event)}])
    print(f"EVENT_DRIVERS before={before} after={after}")
    assert after > before


def test_macro_roles_do_not_invent_a_plan_validity_window() -> None:
    """Driver roles cite the list they receive. The plan window is produced later."""
    from pathlib import Path

    from mokli.trading.teams import role_prompts

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    old = {
        "macro": (
            "## Focus: macro drivers\n\n"
            "Read the macro context for gold from the evidence: US dollar direction, real yields, scheduled\n"
            "events in the calendar window, central-bank tone, and geopolitical risk items that are actually\n"
            "present in the evidence. For each driver you cite, state its bias (bullish, bearish, or\n"
            "neutral for gold) and how strong the evidence is. Flag any event inside the plan's validity\n"
            "window that would make timing matter more than direction.\n"
        ),
        "news": (
            "## Focus: news and event scan\n\n"
            "Scan the calendar and headline items in the evidence for the next sessions: scheduled releases\n"
            "with their impact rating, unscheduled headlines that already moved gold, and anything that\n"
            "falls inside the plan's validity window. Report only items present in the evidence, with their\n"
            "timing relative to the current session. Do not speculate on how price \"should\" react.\n"
        ),
        "event": (
            "## Focus: event risk analysis\n\n"
            "Take the scanned events and assess their risk to a gold position: which events can gap or\n"
            "spike price inside the validity window, what the market appears to be pricing according to the\n"
            "evidence, and where the asymmetry lies (which surprise would hurt a long, which would hurt a\n"
            "short). Rank the events by risk to timing, not by headline size.\n"
        ),
    }
    before = 0
    after = 0
    for stem, previous in old.items():
        text = (roles_dir / f"{stem}.md").read_text(encoding="utf-8")
        assert "inside the validity window" not in text
        assert "plan's validity" not in text
        assert "Do not invent" in text
        before += estimate_prompt_tokens([{"role": "user", "content": previous}])
        after += estimate_prompt_tokens([{"role": "user", "content": text}])
    print(f"VALIDITY_PROMPT before={before} after={after}")


@pytest.mark.asyncio
async def test_scenario_role_uses_candles_and_the_event_note(monkeypatch) -> None:
    """The planner has candles and the event note, not structure or liquidity briefs."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.runtime import run_swarm

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    prompt = (roles_dir / "scenario.md").read_text(encoding="utf-8")
    assert "structure and liquidity evidence" not in prompt
    assert "candle list" in prompt
    assert "event note" in prompt
    assert "Do not invent a structure brief" in prompt
    old = (
        "## Focus: scenario planning\n\n"
        "Lay out bull, base, and bear scenarios for the coming sessions using the event analysis and the\n"
        "structure and liquidity evidence: for each, the trigger that would confirm it, the level that\n"
        "would invalidate it, and the target area it would reach. Keep the scenarios mutually\n"
        "exclusive and tied to evidence levels. You describe the map; the structured decision call\n"
        "picks the path.\n"
    )
    before = estimate_prompt_tokens([{"role": "user", "content": old}])
    after = estimate_prompt_tokens([{"role": "user", "content": prompt}])
    print(f"SCENARIO_PROMPT before={before} after={after}")

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append(
            (
                str(kwargs.get("role")),
                str(kwargs.get("task_text")),
                str(kwargs.get("evidence_text")),
            )
        )
        return "gap risk on the release\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "FOMC holds"

    await run_swarm(
        "gold_news_war_room",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: (task, evidence) for role, task, evidence in seen}
    task, evidence = by_role["Scenario Planner"]
    parsed = json.loads(evidence)
    assert "candles" in parsed
    assert "macroDrivers" not in parsed
    assert "gap risk on the release" in task
    assert "STANCE: wait" in task


@pytest.mark.asyncio
async def test_liquidity_role_reads_candles_not_an_order_book(monkeypatch) -> None:
    """Equal highs are in the bars. An order-book stop cluster is not."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.runtime import run_swarm

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    prompt = (roles_dir / "liquidity.md").read_text(encoding="utf-8")
    assert "stop clusters" not in prompt
    assert "order-book stop cluster" in prompt
    assert "candle evidence" in prompt
    old = (
        "## Focus: liquidity\n\n"
        "Map where liquidity sits from the evidence: equal highs and lows, recent sweeps and their\n"
        "follow-through, untested imbalances, and where stop clusters are likely relative to the\n"
        "current price. State which side is more likely to be hunted before a real move and which\n"
        "level, if traded through, would confirm that the sweep is complete.\n"
    )
    before = estimate_prompt_tokens([{"role": "user", "content": old}])
    after = estimate_prompt_tokens([{"role": "user", "content": prompt}])
    print(f"LIQUIDITY_PROMPT before={before} after={after}")

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((str(kwargs.get("role")), str(kwargs.get("evidence_text"))))
        return "equal highs\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "dollar firm"

    await run_swarm(
        "gold_analysis_committee",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: json.loads(evidence) for role, evidence in seen}
    liquidity = by_role["Liquidity Analyst"]
    assert "candles" in liquidity
    assert "macroDrivers" not in liquidity
    assert "spread_points" not in liquidity
    assert "macroDrivers" in by_role["Macro Analyst"]
    assert "candles" not in by_role["Macro Analyst"]


@pytest.mark.asyncio
async def test_structure_role_reads_swings_in_the_candles_not_a_zone_catalog(monkeypatch) -> None:
    """Swings are in the bars. A validated zone catalog is not."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.runtime import run_swarm

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    prompt = (roles_dir / "structure.md").read_text(encoding="utf-8")
    assert "validated points of interest" not in prompt
    assert "point-of-interest catalog" in prompt
    assert "supply or" in prompt
    assert "context timeframes" not in prompt
    old = (
        "## Focus: price structure\n\n"
        "Describe the structure of the timeframe in the evidence: trend, swing highs and lows, breaks\n"
        "or changes of character, the most recent impulse and correction, and where price sits relative\n"
        "to the nearest validated points of interest. Name the level whose loss would change the\n"
        "structural read. Do not describe a timeframe the evidence does not include.\n"
    )
    before = estimate_prompt_tokens([{"role": "user", "content": old}])
    after = estimate_prompt_tokens([{"role": "user", "content": prompt}])
    print(f"STRUCTURE_PROMPT before={before} after={after}")

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((str(kwargs.get("role")), str(kwargs.get("evidence_text"))))
        return "lower highs\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "dollar firm"

    await run_swarm(
        "gold_analysis_committee",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: json.loads(evidence) for role, evidence in seen}
    structure = by_role["Structure Analyst"]
    assert "candles" in structure
    assert "nearestDemand" not in structure
    assert "nearestSupply" not in structure
    assert "macroDrivers" not in structure
    assert "candles" not in by_role["Risk Officer"]


@pytest.mark.asyncio
async def test_committee_lead_reads_every_specialist_brief(monkeypatch) -> None:
    """The lead attributes points to each brief. Risk's note is not a substitute."""
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    notes = {
        "Macro Analyst": "dollar firm\nSTANCE: sell",
        "Structure Analyst": "lower highs\nSTANCE: sell",
        "Liquidity Analyst": "buy-side above\nSTANCE: wait",
        "Risk Officer": "stop is wide\nSTANCE: wait",
    }
    seen: list[tuple[str, str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        role = str(kwargs.get("role"))
        seen.append((role, str(kwargs.get("task_text")), str(kwargs.get("evidence_text"))))
        return notes.get(role, "noted\nSTANCE: wait")

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "dollar firm"

    await run_swarm(
        "gold_analysis_committee",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    lead_task, lead_evidence = next(
        (task, evidence) for role, task, evidence in seen if role == "Lead Analyst"
    )
    for note in notes.values():
        assert note in lead_task
    parsed = json.loads(lead_evidence)
    assert "candles" not in parsed
    assert "macroDrivers" not in parsed
    risk_only = "Final committee summary.\nrisk: stop is wide\nSTANCE: wait"
    before = estimate_prompt_tokens([{"role": "user", "content": risk_only}])
    after = estimate_prompt_tokens([{"role": "user", "content": lead_task}])
    print(f"LEAD_BRIEFS before={before} after={after}")
    assert after > before


@pytest.mark.asyncio
async def test_debate_desk_advocates_read_the_technical_brief(monkeypatch) -> None:
    """Bull and bear argue from the technical note. They do not receive the candle list."""
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        role = str(kwargs.get("role"))
        seen.append((role, str(kwargs.get("task_text")), str(kwargs.get("evidence_text"))))
        if role == "Technical Analyst":
            return "swing high 2310 holds\nSTANCE: buy"
        return "noted\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )

    async def search(query: str) -> str:
        del query
        return "dollar firm"

    await run_swarm(
        "gold_debate_desk",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: (task, evidence) for role, task, evidence in seen}
    technical_task, technical_evidence = by_role["Technical Analyst"]
    bull_task, bull_evidence = by_role["Bull Advocate"]
    bear_task, bear_evidence = by_role["Bear Advocate"]
    risk_task, risk_evidence = by_role["Risk Manager"]
    assert "candles" in json.loads(technical_evidence)
    for evidence in (bull_evidence, bear_evidence, risk_evidence):
        parsed = json.loads(evidence)
        assert "candles" not in parsed
        assert "macroDrivers" not in parsed
    note = "swing high 2310 holds\nSTANCE: buy"
    assert note in bull_task
    assert note in bear_task
    assert note in risk_task
    assert "2310" not in technical_task
    bare = "Analyze XAUUSD (forex). Build the bull case."
    before = estimate_prompt_tokens([{"role": "user", "content": bare}])
    after = estimate_prompt_tokens([{"role": "user", "content": bull_task}])
    print(f"DEBATE_DESK before={before} after={after}")
    assert after > before


@pytest.mark.asyncio
async def test_presets_without_a_macro_role_do_not_search(monkeypatch) -> None:
    """MTF and the debate desk do not read the driver list, so they do not search."""
    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    searches = {"n": 0}

    async def fake_team_role(**_kwargs: object) -> str:
        return "noted\nSTANCE: wait"

    async def search(query: str) -> str:
        del query
        searches["n"] += 1
        return "dollar firm"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.build_agent_market_context",
        lambda *_a, **_k: _market("1h", 112, 2310.0),
    )

    mtf = await run_swarm(
        "gold_mtf_panel",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    debate = await run_swarm(
        "gold_debate_desk",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    assert searches["n"] == 0
    assert "macroDrivers" not in mtf["team_briefing"]
    assert "macroDrivers" not in debate["team_briefing"]
    assert mtf["macro_drivers"] == []
    assert debate["macro_drivers"] == []

    review = await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    assert searches["n"] > 0
    assert "macroDrivers" in review["team_briefing"]
    print(f"MACRO_SKIP panel=0 desk=0 review={searches['n']}")


@pytest.mark.asyncio
async def test_mtf_synthesizer_reads_the_three_briefs_not_a_lead_chart(monkeypatch) -> None:
    """The panel has H1, H4, and D1. The synthesizer is not given a lead-chart structure."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.runtime import run_swarm

    reset_macro_cache_for_tests()
    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    structure = (roles_dir / "structure.md").read_text(encoding="utf-8")
    synth_prompt = (roles_dir / "mtf_synthesizer.md").read_text(encoding="utf-8")
    assert "context timeframes" not in structure
    assert "lead timeframe" not in synth_prompt
    assert "H1, H4, and D1" in synth_prompt

    notes = {
        "H1 Analyst": "hour holds 2310\nSTANCE: buy",
        "H4 Analyst": "four-hour lower high\nSTANCE: sell",
        "D1 Analyst": "daily still bid\nSTANCE: buy",
    }
    seen: list[tuple[str, str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        role = str(kwargs.get("role"))
        seen.append((role, str(kwargs.get("task_text")), str(kwargs.get("evidence_text"))))
        return notes.get(role, "aligned\nSTANCE: wait")

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.build_agent_market_context",
        lambda *_a, **_k: _market("1h", 112, 2310.0),
    )

    await run_swarm(
        "gold_mtf_panel",
        macro_search=lambda _query: "unused",
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    synth_task, synth_evidence = next(
        (task, evidence) for role, task, evidence in seen if role == "MTF Synthesizer"
    )
    for note in notes.values():
        assert note in synth_task
    parsed = json.loads(synth_evidence)
    assert "candles" not in parsed
    assert "higher_timeframes" not in parsed
    bare = "Synthesize MTF bias."
    before = estimate_prompt_tokens([{"role": "user", "content": bare}])
    after = estimate_prompt_tokens([{"role": "user", "content": synth_task}])
    print(f"MTF_BRIEFS before={before} after={after}")
    assert after > before
    assert "2310" in synth_task


@pytest.mark.asyncio
async def test_trend_role_reads_windows_not_an_invented_swing(monkeypatch) -> None:
    """The trend role compares compact windows. A named chart still gets its own candles."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.runtime import run_swarm

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    prompt = (roles_dir / "timeframe.md").read_text(encoding="utf-8")
    assert "higher-timeframe windows" in prompt
    assert "Do not invent a swing" in prompt
    assert "one timeframe's candles" in prompt
    assert "Do not borrow conclusions from other timeframes" not in prompt

    old = (
        "## Focus: your assigned timeframe\n\n"
        "Analyse only the timeframe named in your task (for example H1, H4, or D1) using the evidence for\n"
        "that timeframe: bias, structure, the last completed swing, and the nearest levels above and\n"
        "below the current price. State whether the timeframe currently supports continuation or a\n"
        "pullback and which level would flip its bias. Do not borrow conclusions from other timeframes.\n"
    )
    before = estimate_prompt_tokens([{"role": "user", "content": old}])
    after = estimate_prompt_tokens([{"role": "user", "content": prompt}])
    print(f"TREND_PROMPT before={before} after={after}")

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((str(kwargs.get("role")), str(kwargs.get("evidence_text"))))
        return "window holds\nSTANCE: wait"

    def fake_context(*args: object, **kwargs: object):
        interval = str(kwargs.get("interval") or (args[1] if len(args) > 1 else "1h"))
        closes = {"1h": 2310.0, "4h": 2320.0, "1d": 2330.0, "15m": 2300.0}
        return _market(interval, 1, closes.get(interval, 2310.0))

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: _market("15m", 111, 2300.0),
    )
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.build_agent_market_context",
        fake_context,
    )

    async def search(query: str) -> str:
        del query
        return "DXY steady"

    await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: json.loads(evidence) for role, evidence in seen}
    trend = by_role["Trend Analyst"]
    assert "candles" not in trend
    assert [row["interval"] for row in trend["higher_timeframes"]] == ["1h", "4h", "1d"]
    assert "window_high" in trend["higher_timeframes"][0]
    assert "spread_points" not in trend

    seen.clear()
    await run_swarm(
        "gold_mtf_panel",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    panel = {role: json.loads(evidence) for role, evidence in seen}
    assert "candles" in panel["H1 Analyst"]
    assert "higher_timeframes" not in panel["H1 Analyst"]
    assert "candles" not in panel["MTF Synthesizer"]


@pytest.mark.asyncio
async def test_risk_role_reads_the_quote_spread_not_a_gate(monkeypatch) -> None:
    """Risk sees bid, ask, and spread. It does not see candles, drivers, or a gate verdict."""
    from pathlib import Path

    from mokli.trading.agents.macro_drivers import reset_macro_cache_for_tests
    from mokli.trading.teams import role_prompts
    from mokli.trading.teams.evidence_text import format_market_evidence
    from mokli.trading.teams.runtime import evidence_for_team_role, run_swarm

    roles_dir = Path(role_prompts.__file__).resolve().parents[2] / "agent" / "prompt" / "team_roles"
    risk_prompt = (roles_dir / "risk.md").read_text(encoding="utf-8")
    assert "likely to block" not in risk_prompt
    assert "do not invent a spread" in risk_prompt
    assert "do not predict which" in risk_prompt

    quoted = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[_candle(111, 2300.0)],
        last_close=2300.0,
        atr=2.5,
        sync=MarketSync(ok=True),
        quote_mid=2300.18,
        quote_bid=2300.0,
        quote_ask=2300.35,
    )
    lead = format_market_evidence(quoted)
    shared = json.loads(lead)
    assert "spread_points" not in shared
    assert "candles" in shared

    risk = json.loads(
        await evidence_for_team_role(lead, "Risk Officer", "role:risk", market=quoted)
    )
    technical = json.loads(
        await evidence_for_team_role(lead, "Technical Analyst", "role:structure", market=quoted)
    )
    macro = json.loads(
        await evidence_for_team_role(lead, "Macro News Analyst", "role:macro", market=quoted)
    )
    review = json.loads(
        await evidence_for_team_role(lead, "Review Analyst", "role:lead", market=quoted)
    )
    assert risk["spread_points"] == 35.0
    assert risk["quote_bid"] == 2300.0
    assert risk["quote_ask"] == 2300.35
    assert risk["atr"] == 2.5
    assert "candles" not in risk
    assert "macroDrivers" not in risk
    assert "spread_points" not in technical
    assert "candles" in technical
    assert "spread_points" not in macro
    assert "candles" not in macro
    assert "macroDrivers" not in macro
    assert "spread_points" not in review
    assert "candles" not in review

    missing = _market("15m", 111, 2300.0)
    unchanged = await evidence_for_team_role(lead, "Risk Officer", "role:risk", market=missing)
    assert "spread_points" not in json.loads(unchanged)

    quote_only = await evidence_for_team_role(lead, "Risk Officer", "role:risk")
    before = estimate_prompt_tokens([{"role": "user", "content": quote_only}])
    after = estimate_prompt_tokens([{"role": "user", "content": json.dumps(risk)}])
    print(f"RISK_SPREAD before={before} after={after}")
    assert after > before

    reset_macro_cache_for_tests()
    seen: list[tuple[str, str]] = []

    async def fake_team_role(**kwargs: object) -> str:
        seen.append((str(kwargs.get("role")), str(kwargs.get("evidence_text"))))
        return "stop behind 2290\nSTANCE: wait"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_team_role", fake_team_role)
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.run_market_data_agent",
        lambda *_a, **_k: quoted,
    )
    monkeypatch.setattr(
        "mokli.trading.teams.runtime.build_agent_market_context",
        lambda *_a, **_k: _market("1h", 1, 2310.0),
    )

    async def search(query: str) -> str:
        del query
        return "DXY steady"

    await run_swarm(
        "gold_decision_review",
        macro_search=search,
        macro_events=[],
        macro_now=lambda: 1_700_000_000.0,
    )
    by_role = {role: json.loads(evidence) for role, evidence in seen}
    assert by_role["Risk Officer"]["spread_points"] == 35.0
    assert "candles" not in by_role["Risk Officer"]
    assert "macroDrivers" not in by_role["Risk Officer"]
    assert "spread_points" not in by_role["Technical Analyst"]
    assert "spread_points" not in by_role["Macro News Analyst"]
    assert "spread_points" not in by_role["Trend Analyst"]
    assert "candles" in by_role["Technical Analyst"]
    assert "macroDrivers" in by_role["Macro News Analyst"]
