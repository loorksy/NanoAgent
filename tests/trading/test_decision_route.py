"""A gold buy/sell question names the existing team, then the kernel."""

from __future__ import annotations

import asyncio
import json

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
    tool = RunTradingKernelTool(bus=None, subagent_manager=None)
    payload = json.loads(asyncio.run(tool.execute(decision_review=True)))
    assert payload["decision"] == "wait"
    assert order == ["swarm", "gold_decision_review"]


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
