"""Lonora turn planner — one live recommendation per conversation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanobot.trading.evidence.node_sets import EMPTY_NODES, FULL_ANALYSIS_NODES, MARKET_DATA_NODES
from nanobot.trading.intent_router import IntentKind, RoutedIntent, route_intent
from nanobot.trading.node_planner import select_analysis_nodes
from nanobot.trading.operator_keywords import (
    EXPLICIT_NEW_ANALYSIS_PHRASES,
    wants_gate_report,
)

TurnMode = Literal[
    "full_analysis",
    "recommendation_followup",
    "specialist",
    "conversation",
    "reevaluation",
    "market_data_only",
    "chart_capture",
    "team_swarm",
    "gate_report",
]


@dataclass(frozen=True)
class TurnTools:
    fetch_market_data: bool = False
    capture_charts: bool = False
    run_full_pipeline: bool = False


@dataclass(frozen=True)
class TurnBudget:
    """Hard budgets for planner delegation (Phase I+)."""

    max_subagents: int = 4
    max_spawn_depth: int = 1


@dataclass(frozen=True)
class TurnPlan:
    mode: TurnMode
    intent: RoutedIntent
    emit_stages: bool
    reason: str = ""
    redirected_from_analysis: bool = False
    requested_new_plan: bool = False
    tools: TurnTools = TurnTools()
    nodes: tuple[str, ...] = EMPTY_NODES
    budget: TurnBudget = TurnBudget()
    run_kernel: bool = True


_SPECIALIST_KINDS: frozenset[IntentKind] = frozenset({"price_query"})
_ANALYSIS_KINDS: frozenset[IntentKind] = frozenset(
    {"gold_analysis", "recommendation", "team_swarm"}
)

NO_TOOLS = TurnTools()
FOLLOWUP_TOOLS = TurnTools(fetch_market_data=True)
FULL_TOOLS = TurnTools(fetch_market_data=True, capture_charts=True, run_full_pipeline=True)
CAPTURE_TOOLS = TurnTools(capture_charts=True)
DEFAULT_BUDGET = TurnBudget()


def wants_explicit_new_analysis(message: str) -> bool:
    text = (message or "").lower()
    return any(phrase.lower() in text for phrase in EXPLICIT_NEW_ANALYSIS_PHRASES)


def plan_turn(
    message: str,
    *,
    active_recommendation_live: bool = False,
    reevaluation: bool = False,
) -> TurnPlan:
    intent = route_intent(message)
    if reevaluation:
        return TurnPlan(
            "reevaluation",
            intent,
            emit_stages=True,
            reason="internal_reevaluation",
            tools=FULL_TOOLS,
            nodes=FULL_ANALYSIS_NODES,
            budget=DEFAULT_BUDGET,
        )
    if intent.kind == "price_query":
        return TurnPlan(
            "market_data_only",
            intent,
            emit_stages=False,
            reason="specialist_intent",
            tools=TurnTools(fetch_market_data=True),
            nodes=MARKET_DATA_NODES,
            budget=DEFAULT_BUDGET,
        )
    if intent.kind == "chart_image":
        return TurnPlan(
            "chart_capture",
            intent,
            emit_stages=False,
            reason="chart_image_intent",
            tools=CAPTURE_TOOLS,
            nodes=("visual_capture",),
            budget=DEFAULT_BUDGET,
        )
    if active_recommendation_live:
        requested = wants_explicit_new_analysis(message)
        if wants_gate_report(message) and not requested:
            return TurnPlan(
                "gate_report",
                intent,
                emit_stages=False,
                reason="gate_inquiry_with_live_recommendation",
                redirected_from_analysis=True,
                tools=NO_TOOLS,
                nodes=EMPTY_NODES,
                budget=DEFAULT_BUDGET,
                run_kernel=False,
            )
        return TurnPlan(
            "recommendation_followup",
            intent,
            emit_stages=False,
            reason=(
                "explicit_new_analysis_with_live_recommendation"
                if requested
                else "ambiguous_with_live_recommendation"
            ),
            redirected_from_analysis=True,
            requested_new_plan=requested,
            tools=FOLLOWUP_TOOLS,
            nodes=MARKET_DATA_NODES,
            budget=DEFAULT_BUDGET,
        )
    if intent.kind not in _ANALYSIS_KINDS:
        specialist = intent.kind in _SPECIALIST_KINDS
        return TurnPlan(
            "specialist" if specialist else "conversation",
            intent,
            emit_stages=False,
            reason="specialist_intent" if specialist else "no_trade_signal",
            tools=NO_TOOLS,
            nodes=EMPTY_NODES,
            budget=DEFAULT_BUDGET,
        )
    if intent.kind == "team_swarm":
        return TurnPlan(
            "team_swarm",
            intent,
            emit_stages=True,
            reason="no_active_recommendation",
            tools=FULL_TOOLS,
            nodes=FULL_ANALYSIS_NODES,
            budget=DEFAULT_BUDGET,
        )
    return TurnPlan(
        "full_analysis",
        intent,
        emit_stages=True,
        reason="no_active_recommendation",
        tools=FULL_TOOLS,
        nodes=select_analysis_nodes(message, intent),
        budget=DEFAULT_BUDGET,
    )
