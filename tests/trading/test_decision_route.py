"""A gold buy/sell question names the existing team, then the kernel."""

from __future__ import annotations

import asyncio
import json

from mokli.agent.hook import AgentHook
from mokli.agent.tools.context import RequestContext
from mokli.trading.decision_route import is_gold_decision_question
from mokli.trading.gold_intent_context import gold_intent_runtime_context


def test_decision_review_runs_the_team_before_the_kernel(monkeypatch) -> None:
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool

    order: list[str] = []

    async def fake_swarm(*_args, **_kwargs):
        order.append("swarm")
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

    tool = RunTradingKernelTool(bus=None, subagent_manager=None)
    with turn_session_scope(TurnSession()) as turn:
        payload = json.loads(asyncio.run(tool.execute(decision_review=True)))
        assert payload["decision"] == "wait"
        assert order == ["swarm", "gold_decision_review"]
        assert turn.decision_wire
        again = json.loads(asyncio.run(tool.execute(decision_review=True)))
        assert again["decision"] == "wait"
        assert order == ["swarm", "gold_decision_review"]


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
