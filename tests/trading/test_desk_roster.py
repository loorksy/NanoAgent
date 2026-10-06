"""Persistent desk roster and per-role tool lists."""

from __future__ import annotations

import pytest

from mokli.session.manager import SessionManager
from mokli.trading.desk.roster import desk_session_key, roster, standing_roles
from mokli.trading.desk.sessions import ensure_desk_session, seed_standing_sessions
from mokli.trading.policy_guard import PolicyViolation, validate_tool_call
from mokli.trading.teams.runtime import list_presets, load_preset
from mokli.trading.turn_session import TurnSession, turn_session_scope


def test_desk_session_key_is_stable(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    first = ensure_desk_session(sessions, "lead_analysis")
    second = ensure_desk_session(sessions, "lead_analysis")
    assert first.key == second.key == desk_session_key("lead_analysis")
    assert first.metadata["desk_role_id"] == "lead_analysis"


def test_seed_creates_leads_clerk_and_journal_only(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    keys = set(seed_standing_sessions(sessions))
    standing = {role.session_key for role in standing_roles()}
    assert keys == standing
    assert desk_session_key("macro_analyst") not in keys
    assert desk_session_key("clerk") in keys
    assert desk_session_key("journal") in keys


def test_roster_covers_preset_agents() -> None:
    known = {role.role_id for role in roster()}
    for name in list_presets():
        preset = load_preset(name)
        for agent in preset.agents:
            assert agent.id in known


def test_lead_may_run_the_team_and_not_the_kernel() -> None:
    with turn_session_scope(TurnSession(session_key="desk:lead_analysis", is_subagent=False)):
        permit = validate_tool_call("run_trading_team", {"preset": "gold_news_war_room"})
        assert permit.tool_name == "run_trading_team"
        with pytest.raises(PolicyViolation):
            validate_tool_call("analyze_gold", {})
        with pytest.raises(PolicyViolation):
            validate_tool_call("run_trading_kernel", {})
        with pytest.raises(PolicyViolation):
            validate_tool_call("mt5_confirm_order", {"confirm": True})


def test_analyst_cannot_run_the_team() -> None:
    with turn_session_scope(TurnSession(session_key="desk:macro_analyst", is_subagent=True)):
        with pytest.raises(PolicyViolation):
            validate_tool_call("run_trading_team", {})
        permit = validate_tool_call("fetch_evidence", {})
        assert permit.args["symbol"] == "XAUUSD"


def test_clerk_cannot_confirm() -> None:
    with turn_session_scope(TurnSession(session_key="desk:clerk", is_subagent=False)):
        with pytest.raises(PolicyViolation):
            validate_tool_call("mt5_confirm_order", {"proposal_id": "x", "confirm": True})


def test_ordinary_subagent_still_cannot_spawn() -> None:
    with turn_session_scope(TurnSession(session_key="agent_api:operator", is_subagent=True)):
        with pytest.raises(PolicyViolation, match="Subagents cannot call spawn"):
            validate_tool_call("spawn", {"task": "nested"})
