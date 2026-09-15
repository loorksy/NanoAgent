"""Tests for Phase K dynamic full-analysis subsets and gate_report path."""

import json

import pytest

from nanobot.trading.evidence import ANALYSIS_WITHOUT_VISUAL_NODES, FULL_ANALYSIS_NODES
from nanobot.trading.policy_guard import validate_turn_plan
from nanobot.trading.recommendations.gate_report import (
    build_gate_report_artifact,
    build_gate_report_result,
)
from nanobot.bus.events import OUTBOUND_META_AGENT_UI
from nanobot.trading.turn_executor import execute_gate_report_path
from nanobot.trading.turn_planner import plan_turn


def test_plan_turn_quick_analysis_omits_visual_capture() -> None:
    turn = plan_turn("حلل الذهب بسرعة بدون شارت")
    assert turn.mode == "full_analysis"
    assert "visual_capture" not in turn.nodes
    assert turn.nodes == ANALYSIS_WITHOUT_VISUAL_NODES


def test_plan_turn_gate_report_with_live_plan() -> None:
    turn = plan_turn("لماذا محجوب؟", active_recommendation_live=True)
    assert turn.mode == "gate_report"
    assert turn.run_kernel is False
    assert turn.nodes == ()


def test_shadow_off_keeps_quick_analysis_subset() -> None:
    turn = plan_turn("quick gold analysis")
    validated = validate_turn_plan(turn, shadow_mode=False)
    assert validated.executed_nodes == ANALYSIS_WITHOUT_VISUAL_NODES
    assert "visual_capture" not in validated.executed_nodes


def test_shadow_on_expands_quick_analysis_to_full_graph() -> None:
    turn = plan_turn("quick gold analysis")
    validated = validate_turn_plan(turn, shadow_mode=True)
    assert validated.executed_nodes == FULL_ANALYSIS_NODES
    assert "shadow_expanded_to_full_graph" in validated.adjustments


def test_build_gate_report_artifact_from_stored_row() -> None:
    row = {
        "id": "rec-1",
        "direction": "buy",
        "gate_json": json.dumps(
            [
                {"id": "G1", "status": "pass", "reason_ar": "ok"},
                {"id": "G3", "status": "fail", "reason_ar": "blocked"},
            ]
        ),
    }
    artifact = build_gate_report_artifact(row, locale="en")
    assert artifact["type"] == "gate_report"
    assert artifact["payload"]["allowed"] is False
    assert artifact["payload"]["vetoedBy"] == "G3"
    assert len(artifact["payload"]["verdicts"]) == 2


@pytest.mark.asyncio
async def test_execute_gate_report_path() -> None:
    live = {
        "id": "rec-1",
        "direction": "sell",
        "entry": 2400.0,
        "stop_loss": 2415.0,
        "targets": [2380.0],
        "status": "waiting",
        "confidence": 0.7,
        "summary": "Sell plan",
        "interval": "15m",
        "gate_json": json.dumps([{"id": "G1", "status": "pass", "reason_ar": "ok"}]),
    }
    turn = plan_turn("why blocked?", active_recommendation_live=True)
    result = await execute_gate_report_path(
        turn,
        text="why blocked?",
        channel="websocket",
        chat_id="ws:1",
        live=live,
    )
    assert result is not None
    assert result.metadata[OUTBOUND_META_AGENT_UI]["data"]["artifacts"][0]["type"] == "gate_report"


def test_build_gate_report_result_without_live_plan() -> None:
    result = build_gate_report_result(None, locale="en")
    assert result.decision.decision == "wait"
