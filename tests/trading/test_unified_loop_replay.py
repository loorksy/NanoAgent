"""CI replay harness — scripted tool transcripts vs both stacks (Group B/C)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanobot.trading.policy_guard import PolicyViolation, validate_tool_call
from nanobot.trading.shadow import replay_divergence
from nanobot.trading.turn_session import TurnSession, turn_session_scope

_FIXTURES = Path(__file__).parent / "fixtures" / "unified_replay"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _run_unified_script(script: list[dict], *, is_subagent: bool = False) -> dict:
    session = TurnSession(is_subagent=is_subagent)
    tools: list[str] = []
    kernel = False
    error = None
    with turn_session_scope(session):
        for step in script:
            name = step["tool"]
            args = dict(step.get("args") or {})
            try:
                validate_tool_call(name, args, is_subagent=is_subagent)
                tools.append(name)
                if name in {"run_trading_kernel", "analyze_gold"}:
                    kernel = True
                    session.kernel_ran = True
                    session.kernel_decision = step.get("decision", "wait")
                if name == "fetch_evidence":
                    for node in args.get("nodes") or []:
                        if node not in session.nodes_fetched:
                            session.nodes_fetched.append(node)
            except PolicyViolation as exc:
                error = exc.reason
                break
    return {
        "tools": tools,
        "kernel": kernel,
        "decision": session.kernel_decision,
        "nodes": list(session.nodes_fetched),
        "error": error,
    }


@pytest.mark.parametrize(
    "filename",
    [
        "price.json",
        "chart.json",
        "followup.json",
        "gate_inquiry.json",
        "full_analysis.json",
        "live_rec_lock.json",
        "subagent_forbidden.json",
    ],
)
def test_replay_fixture(filename: str) -> None:
    fixture = _load_fixture(filename)
    result = _run_unified_script(
        fixture["unified_script"],
        is_subagent=bool(fixture.get("is_subagent")),
    )
    expected = fixture["expect"]
    if expected.get("error_substring"):
        assert result["error"]
        assert expected["error_substring"] in result["error"]
    else:
        assert result["error"] is None
    if "kernel" in expected:
        assert result["kernel"] is expected["kernel"]
    if "tools" in expected:
        assert result["tools"] == expected["tools"]
    old = fixture.get("legacy")
    if old:
        flags = replay_divergence(
            old_decision=old.get("decision"),
            new_decision=result["decision"],
            old_kernel=bool(old.get("kernel")),
            new_kernel=result["kernel"],
            old_nodes=old.get("nodes"),
            new_nodes=result["nodes"],
        )
        assert "side_mismatch" not in flags
