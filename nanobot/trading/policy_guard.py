"""Policy Guard — validate TurnPlan against Lonora Hard Law (Phase I)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from loguru import logger

from nanobot.trading.evidence.graph import DEFAULT_ANALYSIS_GRAPH, EvidenceGraph, graph_for_nodes
from nanobot.trading.evidence.node_sets import (
    FULL_ANALYSIS_NODES,
    SYNTHESIS_REQUIRED_NODES,
    mode_requires_synthesis,
)
from nanobot.trading.capabilities.catalog import CARD_REGISTRY, get_card
from nanobot.trading.evidence.nodes import NODE_REGISTRY
from nanobot.trading.turn_planner import TurnBudget, TurnPlan


class PolicyViolation(Exception):
    """Turn plan cannot be executed under Hard Law."""

    def __init__(self, reason: str, plan: TurnPlan) -> None:
        super().__init__(reason)
        self.reason = reason
        self.plan = plan


@dataclass(frozen=True)
class ValidatedPlan:
    """Planner output after Policy Guard normalization."""

    plan: TurnPlan
    planned_nodes: tuple[str, ...]
    executed_nodes: tuple[str, ...]
    executed_graph: EvidenceGraph
    shadow_mode: bool
    adjustments: tuple[str, ...]


def _normalize_capabilities(plan: TurnPlan) -> tuple[TurnPlan, list[str]]:
    adjustments: list[str] = []
    if not plan.capability_cards:
        return plan, adjustments

    unknown = sorted(set(plan.capability_cards) - set(CARD_REGISTRY))
    if unknown:
        raise PolicyViolation(
            f"Unknown capability cards: {', '.join(unknown)}",
            plan,
        )

    requested_spawn = sum(get_card(card_id).max_subagents for card_id in plan.capability_cards)
    if requested_spawn > plan.budget.max_subagents:
        adjustments.append(
            f"capability_spawn_budget_capped:{requested_spawn}->{plan.budget.max_subagents}"
        )
    return plan, adjustments


def _normalize_budget(budget: TurnBudget) -> tuple[TurnBudget, list[str]]:
    adjustments: list[str] = []
    normalized = budget
    if budget.max_spawn_depth > 1:
        normalized = replace(budget, max_spawn_depth=1)
        adjustments.append("clamped_spawn_depth_to_1")
    if budget.max_subagents < 1:
        normalized = replace(budget, max_subagents=1)
        adjustments.append("clamped_max_subagents_to_1")
    if budget.max_subagents > 4:
        normalized = replace(budget, max_subagents=4)
        adjustments.append("clamped_max_subagents_to_4")
    return normalized, adjustments


def _normalize_nodes(plan: TurnPlan) -> tuple[tuple[str, ...], list[str]]:
    adjustments: list[str] = []
    nodes = tuple(plan.nodes)

    unknown = sorted(set(nodes) - set(NODE_REGISTRY))
    if unknown:
        raise PolicyViolation(
            f"Unknown evidence nodes: {', '.join(unknown)}",
            plan,
        )

    if mode_requires_synthesis(plan.mode):
        missing = sorted(SYNTHESIS_REQUIRED_NODES - set(nodes))
        if missing:
            merged = tuple(sorted(set(nodes) | SYNTHESIS_REQUIRED_NODES))
            adjustments.append(f"injected_required_nodes:{','.join(missing)}")
            nodes = merged

    return nodes, adjustments


def validate_turn_plan(plan: TurnPlan, *, shadow_mode: bool = True) -> ValidatedPlan:
    """Validate and normalize a turn plan; resolve executed graph (shadow expands to full)."""
    budget, budget_adjustments = _normalize_budget(plan.budget)
    capability_plan, capability_adjustments = _normalize_capabilities(
        replace(plan, budget=budget)
    )
    planned_nodes, node_adjustments = _normalize_nodes(capability_plan)
    adjustments = tuple(budget_adjustments + capability_adjustments + node_adjustments)

    normalized_plan = capability_plan
    if planned_nodes is not capability_plan.nodes:
        normalized_plan = replace(capability_plan, nodes=planned_nodes)

    if shadow_mode and mode_requires_synthesis(plan.mode):
        executed_nodes = FULL_ANALYSIS_NODES
        executed_graph = DEFAULT_ANALYSIS_GRAPH
        if frozenset(planned_nodes) != frozenset(executed_nodes):
            adjustments = (*adjustments, "shadow_expanded_to_full_graph")
    else:
        executed_nodes = planned_nodes
        executed_graph = graph_for_nodes(frozenset(executed_nodes))

    return ValidatedPlan(
        plan=normalized_plan,
        planned_nodes=planned_nodes,
        executed_nodes=executed_nodes,
        executed_graph=executed_graph,
        shadow_mode=shadow_mode,
        adjustments=adjustments,
    )


def log_planner_shadow(validated: ValidatedPlan) -> None:
    """Emit structured shadow metrics comparing planned vs executed nodes."""
    planned = list(validated.planned_nodes)
    executed = list(validated.executed_nodes)
    if planned == executed and not validated.adjustments:
        return
    logger.info(
        "Planner shadow mode={} turn_mode={} planned_nodes={} executed_nodes={} adjustments={}",
        validated.shadow_mode,
        validated.plan.mode,
        planned,
        executed,
        list(validated.adjustments),
    )
