"""The kernel decision card uses only fields the result actually has."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from mokli.agent.tools.context import RequestContext, request_context
from mokli.agent_api.events import translate_runtime_event
from mokli.agent_api.results import validate_payload
from mokli.events import DecisionCompletedEvent
from mokli.trading.result_wire import decision_card_payload
from mokli.trading.turn_session import TurnSession, turn_session_scope


def _result(**overrides: object) -> SimpleNamespace:
    recommendation = SimpleNamespace(
        entry=2301.5,
        stop_loss=2294.0,
        targets=[2312.0, "nope"],
        entry_zone=SimpleNamespace(low=2300.0, high=2302.0),
        rr=2.1,
        net_rr=1.9,
        invalidation_rule="close back under the break",
        validity_candles=8,
        alternative_scenario="wait for a retest",
    )
    decision = SimpleNamespace(
        decision="buy",
        confidence=0.62,
        summary="Hour break with the four-hour trend.",
        key_reasons=["hour break", ""],
        gate_chain=SimpleNamespace(
            verdicts=[
                SimpleNamespace(id="G1", status="pass", reason=""),
                SimpleNamespace(id="G6", status="veto", reason="spread wide"),
                SimpleNamespace(id="G9", status="unavailable", reason=""),
            ]
        ),
        recommendation=recommendation,
    )
    result = SimpleNamespace(
        decision=decision,
        recommendation_id="rec-1",
        team_agents=[
            {"status": "done", "summary": "note\nSTANCE: buy"},
            {"status": "done", "summary": "note\nSTANCE: buy"},
            {"status": "done", "summary": "note\nSTANCE: wait"},
        ],
        market=SimpleNamespace(symbol="XAUUSD", interval="15m", candles=[1, 2, 3]),
    )
    for key, value in overrides.items():
        setattr(result, key, value)
    return result


def test_decision_card_keeps_only_real_fields() -> None:
    payload = decision_card_payload(_result())
    assert payload is not None
    assert payload["verdict"] == "buy"
    assert payload["entry"] == 2301.5
    assert payload["stop"] == 2294.0
    assert payload["targets"] == [2312.0]
    assert payload["reasons"] == ["hour break"]
    assert payload["gates_passed"] == ["G1"]
    assert payload["blockers"] == ["spread wide"]
    assert "risk_pct" not in payload
    assert payload["entry_zone"] == {"low": 2300.0, "high": 2302.0}
    assert payload["agreement"] == {"stance": "buy", "agreeing": 2, "votes": 3}
    assert payload["data_sources"] == ["market:XAUUSD:15m"]
    assert "candles" not in payload
    assert validate_payload("decision", payload) == []


def test_gate_risk_fraction_becomes_percent_points() -> None:
    result = _result()
    result.decision.gate_chain.verdicts.append(
        SimpleNamespace(id="G20", status="pass", reason="", evidence={"risk_pct": 0.01})
    )
    payload = decision_card_payload(result)
    assert payload is not None
    assert payload["risk_pct"] == 1.0
    assert "G20" in payload["gates_passed"]


def test_missing_verdict_is_not_a_card() -> None:
    assert decision_card_payload(SimpleNamespace()) is None
    assert decision_card_payload(SimpleNamespace(decision=SimpleNamespace(decision="hold"))) is None


def test_translate_decision_is_structured_not_a_tool() -> None:
    payload = decision_card_payload(_result())
    assert payload is not None
    event = DecisionCompletedEvent(session_key="agent:s_1", payload=payload)
    translated = translate_runtime_event(event)
    assert translated is not None
    assert translated["kind"] == "structured"
    assert translated["data"]["type"] == "decision"
    assert translated["data"]["payload"]["verdict"] == "buy"
    assert translate_runtime_event(DecisionCompletedEvent(session_key="", payload=payload)) is None


def test_kernel_publishes_one_card_and_a_replay_publishes_none(monkeypatch) -> None:
    import mokli.agent.tools.trading_kernel as kernel_tool
    from mokli.agent.tools.base import ToolResult

    published: list[object] = []

    class _Bus:
        async def publish(self, event: object) -> None:
            published.append(event)

    result = _result()

    async def fake_kernel(**_kwargs: object) -> SimpleNamespace:
        return result

    async def fake_swarm(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {"team_briefing": ""}

    async def fake_prefetch(_interval: str, _turn: object) -> None:
        return None

    monkeypatch.setattr(kernel_tool, "run_trading_kernel", fake_kernel)
    monkeypatch.setattr(kernel_tool, "result_to_wire", lambda _result: {"decision": "buy"})
    monkeypatch.setattr(kernel_tool, "_prefetch_synthesis_evidence", fake_prefetch)
    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", fake_swarm)

    tool = kernel_tool.RunTradingKernelTool(bus=_Bus(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="chat", session_key="agent:s_1")
    with request_context(ctx), turn_session_scope(TurnSession()):
        first = json.loads(asyncio.run(tool.execute(decision_review=True)))
        second = json.loads(asyncio.run(tool.execute(decision_review=True)))
    assert first["decision"] == "buy"
    assert second["decision"] == "buy"
    assert len(published) == 1
    assert isinstance(published[0], DecisionCompletedEvent)
    assert published[0].payload["verdict"] == "buy"
    assert published[0].payload["agreement"]["agreeing"] == 2

    async def blocked(*_args: object, **_kwargs: object) -> ToolResult:
        return ToolResult.error("live plan")

    monkeypatch.setattr("mokli.trading.tool_errors.live_plan_block_if_any", blocked)
    with request_context(ctx), turn_session_scope(TurnSession()):
        refused = asyncio.run(tool.execute(decision_review=True))
    assert "live plan" in str(refused)
    assert len(published) == 1
