"""Minimal turn planner for gold trading entry points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanobot.trading.intent_router import IntentKind, RoutedIntent, route_intent

TurnMode = Literal[
    "market_data_only",
    "full_analysis",
    "general_chat",
]


@dataclass(frozen=True)
class TurnPlan:
    mode: TurnMode
    intent: RoutedIntent
    emit_stages: bool


def plan_turn(message: str) -> TurnPlan:
    intent = route_intent(message)
    if intent.kind == "price_query":
        return TurnPlan("market_data_only", intent, emit_stages=True)
    if intent.kind in ("gold_analysis", "recommendation"):
        return TurnPlan("full_analysis", intent, emit_stages=True)
    return TurnPlan("general_chat", intent, emit_stages=False)
