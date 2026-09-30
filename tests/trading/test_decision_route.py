"""A gold buy/sell question names the existing team, then the kernel."""

from __future__ import annotations

import asyncio
import json

from mokli.agent.hook import AgentHook
from mokli.agent.tools.context import RequestContext, request_context
from mokli.trading.decision_route import is_gold_decision_question
from mokli.trading.gold_intent_context import gold_intent_runtime_context


def test_live_plan_skips_the_review_team(tmp_path, monkeypatch) -> None:
    """A live plan is graded once. The review team does not run and is not discarded."""
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool
    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.turn_session import TurnSession, turn_session_scope
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        FinalDecisionResult,
        MarketSync,
    )

    session_key = "websocket:live-blocks-review"
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
                execution_state="valid_now",
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
    calls = {"swarm": 0, "evidence": 0, "resolve": 0, "kernel": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        return {"team_briefing": "should not run"}

    async def fake_prefetch(_interval, _turn):
        calls["evidence"] += 1

    async def fake_kernel(**_kwargs):
        calls["kernel"] += 1
        return object()

    def _resolve(*_args, **_kwargs):
        calls["resolve"] += 1
        quote = type("Q", (), {"mid": 2402.0, "bid": 2401.5, "ask": 2402.5})()
        return quote, "metaapi"

    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel._prefetch_synthesis_evidence",
        fake_prefetch,
    )
    monkeypatch.setattr("mokli.agent.tools.trading_kernel.run_trading_kernel", fake_kernel)
    def _direct(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)

    tool = RunTradingKernelTool(bus=object(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key=session_key)
    with request_context(ctx), turn_session_scope(TurnSession()):
        first = json.loads(asyncio.run(tool.execute(decision_review=True)))
        second = json.loads(asyncio.run(tool.execute(decision_review=True)))
    assert first["reason_key"] == "trading.live_plan_active"
    assert second["reason_key"] == "trading.live_plan_active"
    assert calls == {"swarm": 0, "evidence": 0, "resolve": 1, "kernel": 0}
    print("LIVE_PLAN_TEAM swarm=0 evidence=0 quotes=1")


def test_force_new_plan_still_runs_the_review_team(tmp_path, monkeypatch) -> None:
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool
    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.turn_session import TurnSession, turn_session_scope
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        FinalDecisionResult,
        MarketSync,
    )

    session_key = "websocket:force-new-still-reviews"
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
    called: list[str] = []

    async def fake_swarm(*_args, **_kwargs):
        called.append("swarm")
        return {"team_briefing": "replacement"}

    async def fake_kernel(**kwargs):
        called.append(str(kwargs.get("force_new_plan")))
        return object()

    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.agent.tools.trading_kernel.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel.result_to_wire",
        lambda _result: {"decision": "wait"},
    )
    tool = RunTradingKernelTool(bus=object(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key=session_key)
    with request_context(ctx), turn_session_scope(TurnSession()):
        payload = json.loads(asyncio.run(tool.execute(decision_review=True, force_new_plan=True)))
    assert payload["decision"] == "wait"
    assert called == ["swarm", "True"]


def test_decision_review_runs_the_team_before_the_kernel(monkeypatch) -> None:
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool

    order: list[str] = []

    seen_bus: list[object] = []
    seen_rounds: list[object] = []

    async def fake_swarm(*_args, **kwargs):
        order.append("swarm")
        seen_bus.append(kwargs.get("bus"))
        seen_rounds.append(kwargs.get("max_review_rounds"))
        return {"team_briefing": "technical then review"}

    async def fake_kernel(**kwargs):
        order.append(str(kwargs.get("team_mode")))
        assert kwargs.get("team_briefing") == "technical then review"
        return object()

    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.agent.tools.trading_kernel.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel.result_to_wire",
        lambda _result: {"decision": "wait"},
    )
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    bus = object()
    tool = RunTradingKernelTool(bus=bus, subagent_manager=None)
    with turn_session_scope(TurnSession()) as turn:
        payload = json.loads(asyncio.run(tool.execute(decision_review=True)))
        assert payload["decision"] == "wait"
        assert order == ["swarm", "gold_decision_review"]
        assert seen_bus == [bus]
        from mokli.trading.teams.runtime import review_round_limit

        assert seen_rounds == [review_round_limit()]
        assert turn.decision_wire
        again = json.loads(asyncio.run(tool.execute(decision_review=True)))
        assert again["decision"] == "wait"
        assert order == ["swarm", "gold_decision_review"]


def test_failed_decision_review_does_not_run_again(monkeypatch) -> None:
    """A failed review is remembered. The next call does not start the team."""
    import time

    from mokli.agent.hook import AgentHook, AgentHookContext
    from mokli.agent.tools.execution import execute_tool_calls
    from mokli.agent.tools.registry import ToolRegistry, is_tool_error_result
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool
    from mokli.providers.base import ToolCallRequest
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"swarm": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        await asyncio.sleep(0.2)
        raise RuntimeError("feed down")

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel._prefetch_synthesis_evidence",
        _noop,
    )

    class _Hook(AgentHook):
        def __init__(self) -> None:
            self.starts = 0

        async def before_execute_tool(
            self,
            context: AgentHookContext,
            tool_call: ToolCallRequest,
            tool: object,
            params: object,
        ) -> None:
            self.starts += 1

    tool = RunTradingKernelTool(bus=object(), subagent_manager=None)
    registry = ToolRegistry()
    registry.register(tool)
    hook = _Hook()
    call = ToolCallRequest(
        id="k1",
        name="run_trading_kernel",
        arguments={"decision_review": True, "gather_missing": True},
    )
    started = time.perf_counter()
    with turn_session_scope(TurnSession()):
        first_results, first_events = asyncio.run(
            execute_tool_calls(
                registry,
                [call],
                concurrent=False,
                external_lookup_counts={},
                workspace_violation_counts={},
                hook=hook,
                context=AgentHookContext(iteration=0, messages=[]),
            )
        )
        second_results, second_events = asyncio.run(
            execute_tool_calls(
                registry,
                [call],
                concurrent=False,
                external_lookup_counts={},
                workspace_violation_counts={},
                hook=hook,
                context=AgentHookContext(iteration=1, messages=[]),
            )
        )
        elapsed = time.perf_counter() - started
        assert calls["swarm"] == 1
        assert hook.starts == 1
        replaced = asyncio.run(
            tool.execute(decision_review=True, force_new_plan=True)
        )
    assert calls["swarm"] == 2
    assert hook.starts == 1
    assert first_events[0]["status"] == "error"
    assert "feed down" in str(first_results[0])
    assert second_events[0]["status"] == "reused"
    assert is_tool_error_result(second_results[0])
    assert "feed down" in str(second_results[0])
    assert "feed down" in str(replaced)
    assert elapsed < 0.35
    print(f"FAILED_REVIEW_REPEAT repeat_swarm=0 elapsed_ms={round(elapsed * 1000)}")


def test_failed_analyze_gold_does_not_run_again(monkeypatch) -> None:
    from mokli.agent.tools.registry import is_tool_error_result
    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"kernel": 0}

    async def fake_kernel(**_kwargs):
        calls["kernel"] += 1
        raise RuntimeError("feed down")

    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    tool = AnalyzeGoldTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        first = asyncio.run(tool.execute())
        second = asyncio.run(tool.execute())
        replaced = asyncio.run(tool.execute(reevaluate=True))
    assert calls["kernel"] == 2
    assert is_tool_error_result(first)
    assert is_tool_error_result(second)
    assert is_tool_error_result(replaced)
    assert "feed down" in str(first)
    assert str(second) == str(first)


def test_missing_swarm_preset_is_not_cached(monkeypatch) -> None:
    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"swarm": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        return {"team_briefing": "ready"}

    async def fake_kernel(**_kwargs):
        return object()

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel._prefetch_synthesis_evidence",
        _noop,
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.result_to_wire",
        lambda _result: {"decision": "wait"},
    )
    tool = AnalyzeGoldTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        missing = asyncio.run(tool.execute(team_mode="swarm"))
        ran = json.loads(asyncio.run(tool.execute(team_mode="swarm", preset="gold_mtf_panel")))
    assert "preset" in missing.lower()
    assert calls["swarm"] == 1
    assert ran["decision"] == "wait"


def test_failed_trading_team_does_not_run_again(monkeypatch) -> None:
    from mokli.agent.tools.registry import is_tool_error_result
    from mokli.agent.tools.trading_team import RunTradingTeamTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    calls = {"swarm": 0}

    async def fake_swarm(*_args, **_kwargs):
        calls["swarm"] += 1
        raise RuntimeError("feed down")

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("mokli.agent.tools.trading_team.run_swarm", fake_swarm)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel._prefetch_synthesis_evidence",
        _noop,
    )
    tool = RunTradingTeamTool(bus=object(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1", session_key="websocket:1")
    with request_context(ctx), turn_session_scope(TurnSession()):
        first = asyncio.run(tool.execute(preset="gold_analysis_committee"))
        second = asyncio.run(tool.execute(preset="gold_mtf_panel"))
    assert calls["swarm"] == 1
    assert is_tool_error_result(first)
    assert is_tool_error_result(second)
    assert "feed down" in str(first)
    assert str(second) == str(first)


def test_synthesis_evidence_overlaps_the_review_team(monkeypatch) -> None:
    """Evidence nodes do not read the team brief, so they start with the review."""
    from mokli.agent.tools import trading_kernel as kernel_tool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    started: list[str] = []
    release = asyncio.Event()

    async def fake_swarm(*_args, **_kwargs):
        started.append("swarm")
        if "evidence" in started:
            release.set()
        await release.wait()
        return {"team_briefing": "ready"}

    async def fake_prefetch(_interval, _turn):
        started.append("evidence")
        if "swarm" in started:
            release.set()
        await release.wait()

    async def fake_kernel(**kwargs):
        assert kwargs.get("team_briefing") == "ready"
        return object()

    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)
    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr(kernel_tool, "run_trading_kernel", fake_kernel)
    monkeypatch.setattr(kernel_tool, "result_to_wire", lambda _result: {"decision": "wait"})

    tool = kernel_tool.RunTradingKernelTool(bus=object(), subagent_manager=None)
    with turn_session_scope(TurnSession()):
        payload = json.loads(
            asyncio.run(
                asyncio.wait_for(tool.execute(decision_review=True), timeout=1)
            )
        )
    assert payload["decision"] == "wait"
    assert "swarm" in started
    assert "evidence" in started


def _overlap_pair():
    """Two tasks that each wait until the other has started."""
    started: list[str] = []
    release = asyncio.Event()

    async def mark(name: str) -> None:
        started.append(name)
        if len(started) >= 2:
            release.set()
        await release.wait()

    return started, mark


def test_analyze_gold_debate_overlaps_synthesis_evidence(monkeypatch) -> None:
    """A debate brief does not read evidence, so the nodes start with the crew."""
    from types import SimpleNamespace

    from mokli.agent.tools import trading_kernel as kernel_tool
    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    started, mark = _overlap_pair()

    async def fake_debate(**_kwargs):
        await mark("debate")
        return SimpleNamespace(briefing="bull then bear")

    async def fake_prefetch(_interval, _turn):
        await mark("evidence")

    async def fake_kernel(**kwargs):
        assert kwargs.get("team_briefing") == "bull then bear"
        assert kwargs.get("team_mode") == "debate"
        return object()

    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_debate_crew", fake_debate)
    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.result_to_wire",
        lambda _result: {"decision": "wait"},
    )

    tool = AnalyzeGoldTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        payload = json.loads(
            asyncio.run(asyncio.wait_for(tool.execute(team_mode="debate"), timeout=1))
        )
    assert payload["decision"] == "wait"
    assert started == ["evidence", "debate"] or set(started) == {"evidence", "debate"}


def test_analyze_gold_forwards_the_activity_bus(monkeypatch) -> None:
    """Debate and swarm roles use the same bus as the gold decision review."""
    from types import SimpleNamespace

    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    buses: dict[str, object] = {}

    async def fake_debate(**kwargs):
        buses["debate"] = kwargs.get("bus")
        return SimpleNamespace(briefing="notes")

    async def fake_swarm(*_args, **kwargs):
        buses["swarm"] = kwargs.get("bus")
        return {"team_briefing": "notes"}

    async def fake_kernel(**_kwargs):
        return object()

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_debate_crew", fake_debate)
    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_swarm", fake_swarm)
    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_kernel._prefetch_synthesis_evidence",
        _noop,
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.result_to_wire",
        lambda _result: {"decision": "wait"},
    )
    bus = object()
    tool = AnalyzeGoldTool(bus=bus, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        asyncio.run(tool.execute(team_mode="debate"))
    with turn_session_scope(TurnSession()):
        asyncio.run(tool.execute(team_mode="swarm", preset="gold_mtf_panel"))
    assert buses["debate"] is bus
    assert buses["swarm"] is bus


def test_analyze_gold_core_does_not_prefetch_evidence(monkeypatch) -> None:
    """Core mode has no team to overlap, so the kernel gathers evidence itself."""
    from mokli.agent.tools import trading_kernel as kernel_tool
    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    called: list[str] = []

    async def fake_prefetch(_interval, _turn):
        called.append("evidence")

    async def fake_kernel(**kwargs):
        assert kwargs.get("team_mode") == "core"
        assert kwargs.get("team_briefing") is None
        return object()

    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr("mokli.agent.tools.trading_chart.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.result_to_wire",
        lambda _result: {"decision": "wait"},
    )

    tool = AnalyzeGoldTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        payload = json.loads(asyncio.run(tool.execute(team_mode="core")))
    assert payload["decision"] == "wait"
    assert called == []


def test_analyze_gold_swarm_without_preset_does_not_prefetch(monkeypatch) -> None:
    from mokli.agent.tools import trading_kernel as kernel_tool
    from mokli.agent.tools.trading_chart import AnalyzeGoldTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    called: list[str] = []

    async def fake_prefetch(_interval, _turn):
        called.append("evidence")

    prepared: list[str] = []

    def _prepare(session_key: str | None, **_kwargs: object) -> dict[str, object]:
        prepared.append(session_key or "")
        return {}

    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.current_request_session_key",
        lambda: "websocket:swarm",
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.prepare_for_new_recommendation",
        _prepare,
    )
    tool = AnalyzeGoldTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()):
        raw = asyncio.run(tool.execute(team_mode="swarm"))
    assert "preset" in raw.lower()
    assert called == []
    assert prepared == []


def test_trading_team_overlaps_synthesis_evidence(monkeypatch) -> None:
    from mokli.agent.tools import trading_kernel as kernel_tool
    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.agent.tools.trading_team import RunTradingTeamTool
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    started, mark = _overlap_pair()

    async def fake_swarm(*_args, **_kwargs):
        await mark("swarm")
        return {"team_briefing": "committee"}

    async def fake_prefetch(_interval, _turn):
        await mark("evidence")

    async def fake_kernel(**kwargs):
        assert kwargs.get("team_briefing") == "committee"
        return object()

    monkeypatch.setattr("mokli.agent.tools.trading_team.run_swarm", fake_swarm)
    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr("mokli.trading.kernel.run_trading_kernel", fake_kernel)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_team.result_to_wire",
        lambda _result: {"decision": "wait"},
    )

    tool = RunTradingTeamTool(bus=object(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat-1")
    with request_context(ctx), turn_session_scope(TurnSession()):
        payload = json.loads(
            asyncio.run(
                asyncio.wait_for(
                    tool.execute(preset="gold_analysis_committee"),
                    timeout=1,
                )
            )
        )
    assert payload["final"]["decision"] == "wait"
    assert set(started) == {"swarm", "evidence"}


def test_buy_question_runs_the_kernel_before_the_model() -> None:
    from mokli.agent.runner import AgentRunner
    from mokli.agent.tools.base import Tool
    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    class _Kernel(Tool):
        def __init__(self) -> None:
            self.calls = 0

        @property
        def name(self) -> str:
            return "run_trading_kernel"

        @property
        def description(self) -> str:
            return "kernel"

        @property
        def parameters(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute(self, **kwargs):
            self.calls += 1
            assert kwargs.get("decision_review") is True
            return '{"decision":"wait"}'

    tool = _Kernel()
    registry = ToolRegistry()
    registry.register(tool)
    runner = AgentRunner()
    messages: list[dict] = [{"role": "user", "content": "هل أشتري الذهب؟"}]
    with turn_session_scope(TurnSession(turn_id="t1")), request_context(
        RequestContext(
            channel="websocket",
            chat_id="ws:1",
            session_key="websocket:1",
            original_user_text="هل أشتري الذهب؟",
        )
    ):
        used = asyncio.run(
            runner._prepend_gold_decision(
                tools=registry,
                messages=messages,
                hook=AgentHook(),
                session_key="websocket:1",
                concurrent_tools=False,
                tool_result_cache={},
                external_lookup_counts={},
                workspace_violation_counts={},
            )
        )
    assert used == ["run_trading_kernel"]
    assert tool.calls == 1
    assert messages[-1]["role"] == "tool"
    assert messages[-1]["name"] == "run_trading_kernel"
    assert "wait" in messages[-1]["content"]


def test_plain_question_does_not_run_the_kernel() -> None:
    from mokli.agent.runner import AgentRunner
    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.trading.turn_session import TurnSession, turn_session_scope

    registry = ToolRegistry()
    messages: list[dict] = [{"role": "user", "content": "hello"}]
    with turn_session_scope(TurnSession()), request_context(
        RequestContext(
            channel="websocket",
            chat_id="ws:1",
            original_user_text="hello",
        )
    ):
        used = asyncio.run(
            AgentRunner()._prepend_gold_decision(
                tools=registry,
                messages=messages,
                hook=AgentHook(),
                session_key="websocket:1",
                concurrent_tools=False,
                tool_result_cache={},
                external_lookup_counts={},
                workspace_violation_counts={},
            )
        )
    assert used == []
    assert len(messages) == 1


def test_wire_includes_market_source_and_gate_risk() -> None:
    from mokli.trading.result_wire import result_to_wire
    from mokli.trading.types import (
        AgentFinalResult,
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        GateChainResult,
        GateVerdict,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="wait",
        confidence=0.4,
        summary="wait",
        key_reasons=["spread"],
        risk_warnings=["news"],
        recommendation=AgentRecommendation(action="wait", entry=2300.0, stop_loss=2290.0, targets=[2320.0]),
        gate_chain=GateChainResult(
            verdicts=[
                GateVerdict(
                    id="G20",
                    name="size",
                    status="pass",
                    evidence={"risk_pct": 0.01},
                )
            ],
            allowed=True,
            confidence_delta=0,
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 2300, 2301, 2299, 2300)],
        last_close=2300.0,
        atr=4.0,
        sync=MarketSync(ok=True),
    )
    payload = result_to_wire(
        AgentFinalResult(
            decision=decision,
            market=market,
            stages=[{"stage": "final_decision", "status": "done"}],
        )
    )
    assert payload["recommendation"]["riskPercent"] == 0.01
    assert payload["dataSources"][0] == "market:XAUUSD:15m"
    assert "final_decision" in payload["dataSources"]
    assert payload["keyReasons"] == ["spread"]
    assert "WAIT" in payload["operatorSummary"]
    assert "agreement" not in payload


def test_agreement_counts_only_explicit_stances() -> None:
    from mokli.trading.result_wire import result_to_wire
    from mokli.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult

    decision = FinalDecisionResult(
        decision="buy",
        confidence=0.6,
        summary="buy",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="buy"),
    )
    agreed = result_to_wire(
        AgentFinalResult(
            decision=decision,
            team_agents=[
                {"status": "done", "summary": "levels hold\nSTANCE: buy"},
                {"status": "done", "summary": "news clear\nSTANCE: buy"},
                {"status": "done", "summary": "conflict\nSTANCE: wait"},
            ],
        )
    )
    assert agreed["agreement"] == {"stance": "buy", "agreeing": 2, "votes": 3}
    missing = result_to_wire(
        AgentFinalResult(
            decision=decision,
            team_agents=[
                {"status": "done", "summary": "STANCE: buy"},
                {"status": "done", "summary": "no stance line"},
            ],
        )
    )
    assert "agreement" not in missing


def test_buy_gold_question_routes_to_kernel_review() -> None:
    assert is_gold_decision_question("هل أشتري الذهب؟") is True
    assert is_gold_decision_question("حلل الذهب الآن") is False
    assert is_gold_decision_question("hello there") is False
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="هل أشتري الذهب؟",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is not None
    assert "decision_review=true" in block.content
    assert "gold_decision_review" in block.content


def test_model_brief_drops_images_and_raw_role_text() -> None:
    from mokli.trading.result_wire import brief_for_model

    image = "data:image/png;base64," + ("A" * 8000)
    transcript = "candle by candle\n" * 400 + "STANCE: wait"
    wire = {
        "decision": "wait",
        "summary": "wait for the level",
        "keyReasons": ["spread"],
        "riskWarnings": ["news"],
        "dataSources": ["market:XAUUSD:15m"],
        "operatorSummary": "WAIT",
        "agreement": {"stance": "wait", "agreeing": 2, "votes": 2},
        "recommendation": {
            "action": "wait",
            "entry": 2300.0,
            "stopLoss": 2290.0,
            "targets": [2320.0],
            "riskPercent": 0.01,
            "invalidationRule": "close back inside the range",
            "rr": 2.0,
        },
        "teamAgents": [
            {"agentId": "technical", "role": "Technical Analyst", "status": "done", "summary": transcript},
        ],
        "chartSnapshots": [{"timeframe": "15m", "image": image}],
        "drawings": [{"points": list(range(200))}],
        "cards": [{"html": "x" * 2000}],
        "gateChain": {
            "allowed": True,
            "verdicts": [{"id": "G1", "name": "spread", "status": "pass", "evidence": {"blob": "y" * 3000}}],
        },
    }
    brief = brief_for_model(wire)
    encoded = json.dumps(brief)
    full = json.dumps(wire)
    assert len(encoded) < len(full) // 5
    assert "data:image" not in encoded
    assert "candle by candle" not in encoded
    assert brief["recommendation"]["stopLoss"] == 2290.0
    assert brief["recommendation"]["riskPercent"] == 0.01
    assert brief["recommendation"]["invalidationRule"] == "close back inside the range"
    assert brief["teamAgents"] == [
        {"agentId": "technical", "role": "Technical Analyst", "status": "done", "stance": "wait"}
    ]
    assert "gateChain" not in brief
    with_gates = brief_for_model(wire, include_gates=True)
    assert with_gates["gateChain"]["verdicts"] == [{"id": "G1", "name": "spread", "status": "pass"}]
    assert "blob" not in json.dumps(with_gates)


def test_model_brief_does_not_repeat_the_operator_summary() -> None:
    from mokli.trading.result_wire import brief_for_model, result_to_wire
    from mokli.trading.types import (
        AgentFinalResult,
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )
    from mokli.utils.helpers import estimate_prompt_tokens

    summary = "Wait for a close back above the broken high before acting. " * 12
    decision = FinalDecisionResult(
        decision="wait",
        confidence=0.4,
        summary=summary,
        key_reasons=["The hour is still inside the prior range."] * 4,
        risk_warnings=["News is due before the next candle."] * 2,
        recommendation=AgentRecommendation(action="wait", interval="15m"),
    )
    wire = result_to_wire(
        AgentFinalResult(
            decision=decision,
            market=AgentMarketContext(
                symbol="XAUUSD",
                interval="15m",
                candles=[Candle(1, 2300, 2301, 2299, 2300)],
                last_close=2300.0,
                atr=4.0,
                sync=MarketSync(ok=True),
            ),
        )
    )
    brief = brief_for_model(wire)
    assert "operatorSummary" in wire
    assert "operatorSummary" not in brief
    assert brief["summary"] == summary.strip() or brief["summary"] == summary
    before = estimate_prompt_tokens(
        [{"role": "tool", "content": json.dumps({**brief, "operatorSummary": wire["operatorSummary"]})}]
    )
    after = estimate_prompt_tokens(
        [{"role": "tool", "content": json.dumps(brief)}]
    )
    assert after < before
    print(f"TOKEN_OPERATOR_SUMMARY before={before} after={after} saved={before - after}")


def _decision_tool(name: str, result: str):
    from mokli.agent.tools.base import Tool

    class _Tool(Tool):
        def __init__(self) -> None:
            self.calls = 0

        @property
        def name(self) -> str:
            return name

        @property
        def description(self) -> str:
            return name

        @property
        def parameters(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute(self, **_kwargs):
            self.calls += 1
            return result

    return _Tool()


def _recording_provider(response):
    from mokli.providers.base import LLMProvider

    class _Provider(LLMProvider):
        def __init__(self) -> None:
            super().__init__(provider_name="fake")
            self.calls: list[dict] = []

        def get_default_model(self) -> str:
            return "fake"

        async def chat(self, **kwargs):
            self.calls.append(kwargs)
            return response

        async def chat_stream(self, **kwargs):
            self.calls.append(kwargs)
            return response

    return _Provider()


def _run_turn(text: str, provider, registry):
    from mokli.agent.runner import AgentRunner, AgentRunSpec
    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.trading.turn_session import TurnSession, turn_session_scope
    from mokli.utils.llm_runtime import LLMRuntime

    spec = AgentRunSpec(
        initial_messages=[{"role": "user", "content": text}],
        tools=registry,
        runtime=LLMRuntime.capture(provider, "fake", context_window_tokens=8000),
        max_iterations=3,
        max_tool_result_chars=4000,
        session_key="websocket:1",
    )
    with turn_session_scope(TurnSession(turn_id="t1")), request_context(
        RequestContext(
            channel="websocket",
            chat_id="ws:1",
            session_key="websocket:1",
            original_user_text=text,
        )
    ):
        return asyncio.run(AgentRunner().run(spec))


def test_gold_decision_answer_omits_the_tool_catalog() -> None:
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.providers.base import LLMResponse, ToolCallRequest

    kernel = _decision_tool("run_trading_kernel", '{"decision":"wait"}')
    quote = _decision_tool("get_gold_quote", '{"mid":1}')
    registry = ToolRegistry()
    registry.register(kernel)
    registry.register(quote)
    provider = _recording_provider(
        LLMResponse(
            content="wait for the level",
            tool_calls=[ToolCallRequest(id="q1", name="get_gold_quote", arguments={})],
            finish_reason="tool_calls",
        )
    )
    result = _run_turn("هل أشتري الذهب؟", provider, registry)
    assert kernel.calls == 1
    assert quote.calls == 0
    assert result.final_content == "wait for the level"
    assert len(provider.calls) == 1
    assert provider.calls[0]["tools"] is None
    assert registry.get_definitions()


def test_failed_gold_decision_still_offers_tools() -> None:
    from mokli.agent.tools.base import ToolResult
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.providers.base import LLMResponse

    kernel = _decision_tool("run_trading_kernel", ToolResult.error("feed down"))
    registry = ToolRegistry()
    registry.register(kernel)
    provider = _recording_provider(LLMResponse(content="the feed failed", finish_reason="stop"))
    result = _run_turn("هل أشتري الذهب؟", provider, registry)
    assert kernel.calls == 1
    assert result.final_content == "the feed failed"
    assert provider.calls[0]["tools"]
    assert any(
        item.get("function", {}).get("name") == "run_trading_kernel"
        or item.get("name") == "run_trading_kernel"
        for item in provider.calls[0]["tools"]
    )


def _scripted_provider(responses: list):
    from mokli.providers.base import LLMProvider

    class _Provider(LLMProvider):
        def __init__(self) -> None:
            super().__init__(provider_name="fake")
            self.calls: list[dict] = []
            self._responses = list(responses)

        def get_default_model(self) -> str:
            return "fake"

        async def chat(self, **kwargs):
            return await self.chat_stream(**kwargs)

        async def chat_stream(self, **kwargs):
            self.calls.append(kwargs)
            return self._responses.pop(0)

    return _Provider()


def test_successful_analysis_stops_the_next_tool_round() -> None:
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.providers.base import LLMResponse, ToolCallRequest

    analysis = _decision_tool("analyze_gold", '{"decision":"wait"}')
    quote = _decision_tool("get_gold_quote", '{"mid":1}')
    registry = ToolRegistry()
    registry.register(analysis)
    registry.register(quote)
    provider = _scripted_provider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(id="a1", name="analyze_gold", arguments={})],
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="wait",
                tool_calls=[ToolCallRequest(id="q1", name="get_gold_quote", arguments={})],
                finish_reason="tool_calls",
            ),
        ]
    )
    result = _run_turn("حلل الذهب الآن", provider, registry)
    assert analysis.calls == 1
    assert quote.calls == 0
    assert result.final_content == "wait"
    assert provider.calls[0]["tools"]
    assert provider.calls[1]["tools"] is None


def test_price_tool_does_not_stop_the_next_round() -> None:
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.providers.base import LLMResponse, ToolCallRequest

    quote = _decision_tool("get_gold_quote", '{"mid":1}')
    registry = ToolRegistry()
    registry.register(quote)
    provider = _scripted_provider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(id="q1", name="get_gold_quote", arguments={})],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="the mid is 1", finish_reason="stop"),
        ]
    )
    result = _run_turn("ما السعر؟", provider, registry)
    assert quote.calls == 1
    assert result.final_content == "the mid is 1"
    assert provider.calls[1]["tools"]


def test_plain_question_still_receives_tools() -> None:
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.providers.base import LLMResponse

    kernel = _decision_tool("run_trading_kernel", '{"decision":"wait"}')
    registry = ToolRegistry()
    registry.register(kernel)
    provider = _recording_provider(LLMResponse(content="hello", finish_reason="stop"))
    result = _run_turn("hello there", provider, registry)
    assert kernel.calls == 0
    assert result.final_content == "hello"
    assert provider.calls[0]["tools"]
