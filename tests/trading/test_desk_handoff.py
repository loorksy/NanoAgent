"""Room handoff and swarm brief persistence."""

from __future__ import annotations

import pytest

from mokli.session.manager import SessionManager
from mokli.trading.desk.board import SwarmControl
from mokli.trading.desk.handoff import DeskHandoffError, authorize_desk_handoff, deliver_handoff
from mokli.trading.desk.roster import desk_session_key
from mokli.trading.policy_guard import PolicyViolation, validate_tool_call
from mokli.trading.teams import runtime as swarm_runtime
from mokli.trading.turn_session import TurnSession, turn_session_scope


def test_specialist_cannot_message_outside_the_room() -> None:
    with pytest.raises(DeskHandoffError, match="outside"):
        authorize_desk_handoff(desk_session_key("macro_analyst"), "clerk", 0)
    with pytest.raises(DeskHandoffError, match="outside"):
        authorize_desk_handoff(desk_session_key("macro_analyst"), "lead_news", 0)


def test_analysis_lead_can_hand_a_brief_to_the_clerk(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    target = deliver_handoff(
        sessions,
        desk_session_key("lead_analysis"),
        "clerk",
        "Proposal brief",
    )
    assert target.role_id == "clerk"
    clerk = sessions.get_or_create(desk_session_key("clerk"))
    assert any("Proposal brief" in message["content"] for message in clerk.messages)


def test_handoff_stops_at_depth_three() -> None:
    with pytest.raises(DeskHandoffError, match="depth"):
        authorize_desk_handoff(desk_session_key("lead_analysis"), "macro_analyst", 3)


@pytest.mark.asyncio
async def test_news_swarm_saves_the_brief_on_the_lead(tmp_path, monkeypatch) -> None:
    sessions = SessionManager(tmp_path)

    def _market(*_args, **_kwargs):
        return object()

    async def _role(**_kwargs):
        return "scanned"

    async def _macro(**_kwargs):
        return []

    monkeypatch.setattr(swarm_runtime, "run_market_data_agent", _market)
    monkeypatch.setattr(swarm_runtime, "format_market_evidence", lambda _market: "{}")
    monkeypatch.setattr(swarm_runtime, "run_team_role", _role)
    monkeypatch.setattr(swarm_runtime, "run_macro_drivers", _macro)
    monkeypatch.setattr(swarm_runtime, "format_team_briefing", lambda _items: "")

    result = await swarm_runtime.run_swarm("gold_news_war_room", sessions=sessions)
    lead = sessions.get_or_create(desk_session_key("lead_news"))
    assert result["preset"] == "gold_news_war_room"
    assert any("scanned" in message["content"] for message in lead.messages)


@pytest.mark.asyncio
async def test_stop_during_the_first_layer_skips_the_synthesizer(monkeypatch) -> None:
    control = SwarmControl()
    layers: list[int] = []

    async def _role(**kwargs):
        layers.append(kwargs["layer"])
        if kwargs["layer"] == 0:
            control.cancel()
        return "frame"

    async def _macro(**_kwargs):
        raise AssertionError("macro should not run after cancel")

    monkeypatch.setattr(swarm_runtime, "run_market_data_agent", lambda *_a, **_k: object())
    monkeypatch.setattr(swarm_runtime, "format_market_evidence", lambda _market: "{}")
    monkeypatch.setattr(swarm_runtime, "run_team_role", _role)
    monkeypatch.setattr(swarm_runtime, "run_macro_drivers", _macro)
    monkeypatch.setattr(swarm_runtime, "format_team_briefing", lambda _items: "")

    result = await swarm_runtime.run_swarm("gold_mtf_panel", control=control)
    assert result["cancelled"] is True
    assert layers
    assert 1 not in layers


def test_clerk_confirm_is_still_a_policy_violation() -> None:
    with turn_session_scope(TurnSession(session_key=desk_session_key("clerk"), is_subagent=False)):
        with pytest.raises(PolicyViolation):
            validate_tool_call("mt5_confirm_order", {"confirm": True})
