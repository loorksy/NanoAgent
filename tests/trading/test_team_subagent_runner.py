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
    assert technical["candles"][0]["t"] == 111
    assert "candles" not in trend
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
