"""A tool call is one activity row. The task text is not a second subagent."""

import asyncio

import pytest

import mokli.agent_api.sessions as sessions_mod
from mokli.agent.hook import AgentHookContext
from mokli.agent.tools.display import phrase_for
from mokli.agent.tools.execution import _execute_tool_call
from mokli.agent_api.sessions import TurnHook
from mokli.providers.base import ToolCallRequest
from mokli.trading.policy_guard import PolicyViolation


class _Hub:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(self, session: str, kind: str, data: dict[str, object], *, run: str | None = None) -> None:
        self.events.append({"session": session, "kind": kind, "data": dict(data), "run": run})


def _hook() -> tuple[TurnHook, _Hub]:
    hub = _Hub()
    return TurnHook(hub, object(), session="s1", run="r1"), hub  # type: ignore[arg-type]


def _ctx() -> AgentHookContext:
    return AgentHookContext(iteration=0, messages=[])


async def test_spawn_is_one_tool_row_and_the_task_stays_in_the_arguments() -> None:
    hook, hub = _hook()
    call = ToolCallRequest(id="c1", name="spawn", arguments={})
    task = "لخّص أخبار الذهب ثم اقترح سيناريو"
    await hook.before_execute_tool(_ctx(), call, object(), {"task": task, "label": "أخبار"})
    await hook.after_execute_tool(_ctx(), call, object(), {"task": task}, "done")

    assert [event["kind"] for event in hub.events] == ["tool", "tool"]
    started, finished = hub.events
    assert started["data"]["display"] == phrase_for("spawn", "started")
    assert started["data"]["name"] == "spawn"
    assert task in str(started["data"]["arguments"])
    assert finished["data"]["display"] == phrase_for("spawn", "finished")
    assert finished["data"]["event"] == "finished"
    assert all(task not in str(event["data"].get("role", "")) for event in hub.events)


async def test_trading_team_tool_does_not_invent_a_parent_subagent() -> None:
    hook, hub = _hook()
    call = ToolCallRequest(id="c2", name="run_trading_team", arguments={})
    await hook.before_execute_tool(
        _ctx(), call, object(), {"preset": "gold_decision_review"},
    )
    await hook.after_execute_tool(_ctx(), call, object(), {"preset": "gold_decision_review"}, "{}")

    assert [event["kind"] for event in hub.events] == ["tool", "tool"]
    assert hub.events[0]["data"]["display"] == phrase_for("run_trading_team", "started")
    assert hub.events[1]["data"]["display"] == phrase_for("run_trading_team", "finished")


async def test_finished_tool_keeps_the_measured_duration(monkeypatch) -> None:
    clock = {"now": 10.0}
    monkeypatch.setattr(sessions_mod.time, "monotonic", lambda: clock["now"])
    hook, hub = _hook()
    call = ToolCallRequest(id="c3", name="get_gold_quote", arguments={})
    await hook.before_execute_tool(_ctx(), call, object(), {"symbol": "XAUUSD"})
    clock["now"] = 13.7
    await hook.after_execute_tool(_ctx(), call, object(), {"symbol": "XAUUSD"}, "bid 2300")

    started, finished = hub.events
    assert "duration_ms" not in started["data"]
    assert finished["data"]["duration_ms"] == 3700


async def test_failed_tool_keeps_the_measured_duration(monkeypatch) -> None:
    clock = {"now": 1.0}
    monkeypatch.setattr(sessions_mod.time, "monotonic", lambda: clock["now"])
    hook, hub = _hook()
    call = ToolCallRequest(id="c4", name="get_gold_quote", arguments={})
    await hook.before_execute_tool(_ctx(), call, object(), {"symbol": "XAUUSD"})
    clock["now"] = 1.2
    await hook.on_execute_tool_error(_ctx(), call, object(), {"symbol": "XAUUSD"}, "timeout")

    started, failed = hub.events
    assert "duration_ms" not in started["data"]
    assert failed["data"]["event"] == "failed"
    assert failed["data"]["duration_ms"] == 200


async def test_policy_block_closes_the_started_tool_row(monkeypatch) -> None:
    clock = {"now": 5.0}
    monkeypatch.setattr(sessions_mod.time, "monotonic", lambda: clock["now"])

    def _deny(name: str, args: dict, **kwargs: object) -> None:
        clock["now"] = 8.7
        raise PolicyViolation("Subagents cannot call spawn")

    monkeypatch.setattr("mokli.trading.policy_guard.validate_tool_call", _deny)
    hook, hub = _hook()
    call = ToolCallRequest(id="c5", name="spawn", arguments={"task": "لخّص"})
    class _Tools:
        def get(self, name: str) -> None:
            return None

    result, event = await _execute_tool_call(
        _Tools(),  # type: ignore[arg-type]
        call,
        {},
        {},
        hook,
        _ctx(),
    )

    assert event["status"] == "error"
    assert "Subagents cannot call spawn" in str(result)
    started, failed = hub.events
    assert [item["kind"] for item in hub.events] == ["tool", "tool"]
    assert started["data"]["event"] == "started"
    assert started["data"]["call_id"] == "c5"
    assert failed["data"]["event"] == "failed"
    assert failed["data"]["call_id"] == "c5"
    assert failed["data"]["display"] == phrase_for("spawn", "failed")
    assert failed["data"]["duration_ms"] == 3700
    assert "Subagents cannot call spawn" in str(failed["data"]["summary"])


async def test_cancel_closes_the_started_tool_row(monkeypatch) -> None:
    clock = {"now": 2.0}
    monkeypatch.setattr(sessions_mod.time, "monotonic", lambda: clock["now"])

    class _Tool:
        async def execute(self, **kwargs: object) -> str:
            clock["now"] = 5.7
            await asyncio.sleep(30)
            return "late"

    class _Tools:
        def get(self, name: str) -> _Tool:
            return _Tool()

        def prepare_call(self, name: str, arguments: object) -> tuple[_Tool, object, None]:
            return _Tool(), arguments, None

    hook, hub = _hook()
    call = ToolCallRequest(id="c6", name="get_gold_quote", arguments={"symbol": "XAUUSD"})

    async def _run() -> None:
        await _execute_tool_call(_Tools(), call, {}, {}, hook, _ctx())  # type: ignore[arg-type]

    task = asyncio.create_task(_run())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    started, failed = hub.events
    assert [item["kind"] for item in hub.events] == ["tool", "tool"]
    assert started["data"]["event"] == "started"
    assert failed["data"]["event"] == "failed"
    assert failed["data"]["call_id"] == "c6"
    assert failed["data"]["display"] == phrase_for("get_gold_quote", "failed")
    assert failed["data"]["duration_ms"] == 3700
    assert "cancelled" in str(failed["data"].get("summary"))
