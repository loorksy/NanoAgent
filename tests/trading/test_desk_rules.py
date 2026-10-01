"""Operator rules cannot weaken Hard Law."""

from __future__ import annotations

import pytest

from mokli.agent.hook import AgentHook, AgentHookContext
from mokli.agent.tools.execution import _execute_tool_call
from mokli.providers.base import ToolCallRequest
from mokli.trading.desk.rules import (
    RULE_KEYS,
    ApprovalRequired,
    DeskRules,
    DeskRuleStore,
    grant_action,
    rules_scope,
)
from mokli.trading.policy_guard import PolicyViolation, validate_tool_call
from mokli.trading.turn_session import TurnSession, turn_session_scope


class _MemorySecrets:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, name: str) -> str:
        return self.data.get(name, "")

    def set(self, name: str, value: str) -> None:
        self.data[name] = value


def test_allow_does_not_restore_a_forbidden_subagent_tool() -> None:
    with rules_scope(DeskRules(python="allow")):
        with turn_session_scope(TurnSession(session_key="agent_api:child", is_subagent=True)):
            with pytest.raises(PolicyViolation, match="Subagents cannot call spawn"):
                validate_tool_call("spawn", {"task": "again"})


def test_deny_blocks_web_fetch_for_an_analyst() -> None:
    with rules_scope(DeskRules(web="deny")):
        with turn_session_scope(TurnSession(session_key="desk:macro_analyst", is_subagent=True)):
            with pytest.raises(PolicyViolation, match="denied web"):
                validate_tool_call("web_fetch", {"url": "https://example.com"})


def test_approve_holds_propose_without_a_confirm_rule() -> None:
    assert "mt5_confirm_order" not in RULE_KEYS
    with rules_scope(DeskRules()):
        with turn_session_scope(TurnSession(session_key="desk:clerk", is_subagent=False)):
            with pytest.raises(ApprovalRequired):
                validate_tool_call("mt5_propose_order", {"symbol": "XAUUSD"})


def test_a_grant_allows_one_propose_call() -> None:
    grant_action("propose_order")
    with rules_scope(DeskRules()):
        with turn_session_scope(TurnSession(session_key="desk:clerk", is_subagent=False)):
            permit = validate_tool_call("mt5_propose_order", {"symbol": "XAUUSD"})
            assert permit.tool_name == "mt5_propose_order"
            with pytest.raises(ApprovalRequired):
                validate_tool_call("mt5_propose_order", {"symbol": "XAUUSD"})


def test_rule_store_round_trip() -> None:
    store = DeskRuleStore(_MemorySecrets())
    saved = store.save(DeskRules(python="deny"), who="operator")
    assert saved.python == "deny"
    assert store.load().python == "deny"


@pytest.mark.asyncio
async def test_approval_does_not_call_the_tool() -> None:
    called = {"execute": False}

    class _Tool:
        async def execute(self, **_kwargs: object) -> str:
            called["execute"] = True
            return "filled"

    class _Tools:
        def prepare_call(self, _name: str, args: dict) -> tuple:
            return _Tool(), args, None

    published: list[dict] = []

    class _Hook(AgentHook):
        async def on_desk_approval(self, event: dict) -> None:
            published.append(event)

    with rules_scope(DeskRules()):
        with turn_session_scope(TurnSession(session_key="desk:clerk", is_subagent=False)):
            result, event = await _execute_tool_call(
                _Tools(),  # type: ignore[arg-type]
                ToolCallRequest(id="c1", name="mt5_propose_order", arguments={}),
                {},
                {},
                _Hook(),
                AgentHookContext(iteration=0, messages=[]),
            )
    assert called["execute"] is False
    assert event["status"] == "approval"
    assert "Waiting for operator approval" in result
    assert published and published[0]["status"] == "pending"
    assert published[0]["actions"] == ["confirm", "cancel"]
