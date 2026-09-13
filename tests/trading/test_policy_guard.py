"""Tests for Phase I Policy Guard and turn-plan node selection."""

import pytest

from nanobot.trading.evidence import FULL_ANALYSIS_NODES, graph_for_nodes
from nanobot.trading.intent_router import route_intent
from nanobot.trading.policy_guard import PolicyViolation, log_planner_shadow, validate_turn_plan
from nanobot.trading.turn_planner import TurnBudget, TurnPlan, plan_turn


def _full_plan(**overrides) -> TurnPlan:
    base = plan_turn("حلل الذهب واعطني توصية")
    return TurnPlan(
        mode=overrides.pop("mode", base.mode),
        intent=overrides.pop("intent", base.intent),
        emit_stages=overrides.pop("emit_stages", base.emit_stages),
        reason=overrides.pop("reason", base.reason),
        tools=overrides.pop("tools", base.tools),
        nodes=overrides.pop("nodes", base.nodes),
        budget=overrides.pop("budget", base.budget),
        **overrides,
    )


def test_plan_turn_full_analysis_declares_all_nodes() -> None:
    turn = plan_turn("حلل الذهب واعطني توصية")
    assert turn.mode == "full_analysis"
    assert frozenset(turn.nodes) == frozenset(FULL_ANALYSIS_NODES)


def test_plan_turn_price_query_declares_market_data_only() -> None:
    turn = plan_turn("كم سعر الذهب؟")
    assert turn.nodes == ("market_data",)


def test_policy_guard_injects_missing_synthesis_nodes() -> None:
    plan = _full_plan(nodes=("market_data", "structure"))
    validated = validate_turn_plan(plan, shadow_mode=False)
    assert "risk" in validated.planned_nodes
    assert any(adj.startswith("injected_required_nodes:") for adj in validated.adjustments)


def test_policy_guard_rejects_unknown_nodes() -> None:
    plan = _full_plan(nodes=("market_data", "not_a_real_node"))
    with pytest.raises(PolicyViolation, match="Unknown evidence nodes"):
        validate_turn_plan(plan)


def test_policy_guard_clamps_spawn_depth() -> None:
    plan = _full_plan(budget=TurnBudget(max_spawn_depth=3))
    validated = validate_turn_plan(plan)
    assert validated.plan.budget.max_spawn_depth == 1
    assert "clamped_spawn_depth_to_1" in validated.adjustments


def test_shadow_mode_expands_subset_to_full_graph() -> None:
    plan = _full_plan(nodes=("market_data", "structure", "liquidity", "supply_demand", "multi_timeframe", "news", "geometry", "risk"))
    validated = validate_turn_plan(plan, shadow_mode=True)
    assert validated.executed_nodes == FULL_ANALYSIS_NODES
    assert "visual_capture" in validated.executed_nodes
    assert "shadow_expanded_to_full_graph" in validated.adjustments


def test_non_shadow_uses_subset_graph() -> None:
    plan = _full_plan(nodes=FULL_ANALYSIS_NODES)
    validated = validate_turn_plan(plan, shadow_mode=False)
    assert validated.executed_nodes == FULL_ANALYSIS_NODES
    assert validated.executed_graph.name == "subset"
    assert validated.executed_graph.layers == graph_for_nodes(frozenset(FULL_ANALYSIS_NODES)).layers


def test_log_planner_shadow_runs_without_error() -> None:
    plan = _full_plan()
    validated = validate_turn_plan(plan, shadow_mode=True)
    log_planner_shadow(validated)


def test_graph_for_nodes_filters_layers() -> None:
    graph = graph_for_nodes(frozenset({"market_data", "news"}))
    assert graph.layers == (("market_data",), ("news",))
