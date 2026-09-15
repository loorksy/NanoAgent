"""Map intents and messages to capability cards (Phase L)."""

from __future__ import annotations

from dataclasses import replace

from nanobot.trading.capabilities.catalog import CARD_REGISTRY, get_card
from nanobot.trading.intent_router import RoutedIntent, resolve_team_preset
from nanobot.trading.operator_keywords import wants_debate, wants_macro_scan, wants_structure_review
from nanobot.trading.turn_planner import TurnBudget, TurnMode, TurnPlan


def select_capability_cards(
    message: str,
    intent: RoutedIntent,
    mode: TurnMode,
) -> tuple[str, ...]:
    if mode == "market_data_only":
        return ("price_quote",)
    if mode == "chart_capture":
        return ("chart_snapshot",)
    if mode == "gate_report":
        return ("gate_report",)
    if mode == "recommendation_followup":
        return ("price_quote",)
    if mode == "team_swarm":
        preset = resolve_team_preset(message) or ""
        if "debate" in preset or wants_debate(message):
            return ("debate",)
        return ("committee",)
    if mode in ("full_analysis", "reevaluation"):
        cards: list[str] = []
        if wants_macro_scan(message):
            cards.append("macro_scan")
        if wants_structure_review(message):
            cards.append("structure_review")
        return tuple(cards)
    return ()


def _merged_nodes(plan: TurnPlan, cards: tuple[str, ...]) -> tuple[str, ...]:
    merged = set(plan.nodes)
    for card_id in cards:
        merged.update(get_card(card_id).required_nodes)
    return tuple(sorted(merged))


def _resolve_team_preset(cards: tuple[str, ...], message: str) -> str | None:
    preset = resolve_team_preset(message)
    if preset:
        return preset
    for card_id in cards:
        card = get_card(card_id)
        if card.team_preset:
            return card.team_preset
    return None


def _resolve_budget(plan: TurnPlan, cards: tuple[str, ...]) -> TurnBudget:
    spawn_cards = [get_card(card_id) for card_id in cards if get_card(card_id).max_subagents > 0]
    if not spawn_cards:
        return plan.budget
    requested = max(card.max_subagents for card in spawn_cards)
    return TurnBudget(
        max_subagents=min(plan.budget.max_subagents, requested),
        max_spawn_depth=plan.budget.max_spawn_depth,
    )


def apply_capability_plan(plan: TurnPlan, message: str) -> TurnPlan:
    """Attach capability cards and derived nodes / preset / budget to a turn plan."""
    cards = select_capability_cards(message, plan.intent, plan.mode)
    if not cards:
        return plan
    unknown = sorted(set(cards) - set(CARD_REGISTRY))
    if unknown:
        raise ValueError(f"Unknown capability cards: {', '.join(unknown)}")
    return replace(
        plan,
        capability_cards=cards,
        nodes=_merged_nodes(plan, cards),
        team_preset=_resolve_team_preset(cards, message),
        budget=_resolve_budget(plan, cards),
    )
