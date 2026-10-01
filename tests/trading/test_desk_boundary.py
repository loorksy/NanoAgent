"""Swarm cards and the credential boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from mokli.trading.code_policy import CodePolicyError, review_python
from mokli.trading.desk.board import reduce_board, team_subagent_event
from mokli.trading.desk.profiles import profile_tools
from mokli.trading.desk.roster import roster
from mokli.trading.policy_guard import MT5_EXECUTION_TOOLS
from mokli.trading.python_sandbox import scrubbed_env
from mokli.trading.teams.subagent_runner import TeamAgentEvent


def test_board_keeps_the_latest_card_per_role() -> None:
    started = team_subagent_event(
        TeamAgentEvent(
            agent_id="h1_analyst",
            role="H1 Analyst",
            status="running",
            layer=0,
            room_id="mtf",
            role_id="h1_analyst",
        ),
        "started",
    )
    finished = team_subagent_event(
        TeamAgentEvent(
            agent_id="h1_analyst",
            role="H1 Analyst",
            status="done",
            summary="higher low",
            layer=0,
            room_id="mtf",
            role_id="h1_analyst",
        ),
        "finished",
    )
    synth = team_subagent_event(
        TeamAgentEvent(
            agent_id="mtf_synthesizer",
            role="MTF Synthesizer",
            status="running",
            layer=1,
            room_id="mtf",
            role_id="mtf_synthesizer",
        ),
        "started",
    )
    cards = reduce_board([started, finished, synth])
    by_id = {card.role_id: card for card in cards}
    assert by_id["h1_analyst"].stage == "finished"
    assert by_id["h1_analyst"].summary == "higher low"
    assert by_id["h1_analyst"].room_id == "mtf"
    assert by_id["mtf_synthesizer"].layer == 1
    assert started["room_id"] == "mtf"
    assert started["role_id"] == "h1_analyst"
    assert started["layer"] == 0


def test_lab_environment_drops_parent_mt5_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MT5_PASSWORD", "secret")
    monkeypatch.setenv("MT5_LOGIN", "1")
    monkeypatch.setenv("MT5_SERVER", "broker")
    env = scrubbed_env()
    assert "MT5_PASSWORD" not in env
    assert "MT5_LOGIN" not in env
    assert "MT5_SERVER" not in env


def test_only_the_clerk_may_propose_and_nobody_confirms() -> None:
    for role in roster():
        tools = profile_tools(role.profile)
        execution = tools & MT5_EXECUTION_TOOLS
        if role.role_id == "clerk":
            assert execution == frozenset({"mt5_propose_order"})
        else:
            assert execution == frozenset()
        assert "mt5_confirm_order" not in tools


def test_lead_contract_states_the_desk_boundary() -> None:
    text = Path("mokli/agent/prompt/composer.py").read_text(encoding="utf-8")
    assert "confirmation stays with the operator" in text
    assert "idle research writes only in the news room" in text


def test_lab_profile_cannot_review_an_order_call() -> None:
    with pytest.raises(CodePolicyError):
        review_python("import MetaTrader5\n")
