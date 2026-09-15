"""Tests for Phase L capability cards."""

import pytest

from nanobot.trading.capabilities import (
    CARD_REGISTRY,
    apply_capability_plan,
    get_card,
    select_capability_cards,
)
from nanobot.trading.policy_guard import validate_turn_plan
from nanobot.trading.turn_planner import TurnPlan, plan_turn


def test_capability_catalog_has_phase_l_cards() -> None:
    assert {"price_quote", "committee", "debate", "macro_scan", "structure_review"} <= set(
        CARD_REGISTRY
    )


def test_select_committee_card_for_team_swarm() -> None:
    turn = plan_turn("شغّل لجنة الذهب")
    assert turn.mode == "team_swarm"
    assert "committee" in turn.capability_cards
    assert turn.team_preset == "gold_analysis_committee"


def test_select_debate_card_for_debate_keywords() -> None:
    turn = plan_turn("gold debate desk")
    assert turn.mode == "team_swarm"
    assert "debate" in turn.capability_cards
    assert turn.team_preset == "gold_debate_desk"


def test_macro_scan_card_adds_news_node() -> None:
    turn = plan_turn("حلل الذهب مع الأخبار والماكرو")
    assert "macro_scan" in turn.capability_cards
    assert "news" in turn.nodes


def test_structure_review_card_adds_structure_nodes() -> None:
    turn = plan_turn("حلل مستويات الدعم والمقاومة للذهب")
    assert turn.mode == "full_analysis"
    assert "structure_review" in turn.capability_cards
    assert "structure" in turn.nodes
    assert "liquidity" in turn.nodes


def test_committee_budget_clamped_to_four() -> None:
    turn = plan_turn("شغّل لجنة الذهب")
    assert turn.budget.max_subagents == 4


def test_policy_guard_rejects_unknown_capability_card() -> None:
    base = plan_turn("حلل الذهب")
    plan = TurnPlan(
        mode=base.mode,
        intent=base.intent,
        emit_stages=base.emit_stages,
        capability_cards=("not_a_card",),
    )
    with pytest.raises(Exception, match="Unknown capability cards"):
        validate_turn_plan(plan)


def test_apply_capability_plan_is_idempotent_for_price() -> None:
    base = plan_turn("كم سعر الذهب؟")
    again = apply_capability_plan(base, "كم سعر الذهب؟")
    assert again.capability_cards == base.capability_cards


def test_committee_card_declares_required_fields() -> None:
    card = get_card("committee")
    assert card.team_preset == "gold_analysis_committee"
    assert card.max_subagents == 5
    assert card.output_schema == "team_briefing"
    assert card.cost_estimate >= 1
