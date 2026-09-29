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

    seen_bus: list[object] = []

    async def fake_swarm(*_args, **kwargs):
        order.append("swarm")
        seen_bus.append(kwargs.get("bus"))
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
