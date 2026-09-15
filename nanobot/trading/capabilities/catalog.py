"""Capability card catalog — Phase L."""

from __future__ import annotations

from dataclasses import dataclass

from nanobot.trading.evidence.node_sets import FULL_ANALYSIS_NODES, MARKET_DATA_NODES

CapabilityId = str


@dataclass(frozen=True)
class CapabilityCard:
    """Planner-readable capability with nodes, budget, and optional team preset."""

    id: CapabilityId
    required_nodes: tuple[str, ...]
    max_subagents: int = 0
    cost_estimate: int = 1
    output_schema: str = "evidence_brief"
    team_preset: str | None = None
    spawn_role: str | None = None
    preflight_prompt: str = ""


_CARDS: tuple[CapabilityCard, ...] = (
    CapabilityCard(
        id="price_quote",
        required_nodes=MARKET_DATA_NODES,
        cost_estimate=1,
        output_schema="price_quote",
    ),
    CapabilityCard(
        id="chart_snapshot",
        required_nodes=("visual_capture",),
        cost_estimate=2,
        output_schema="chart_snapshot",
    ),
    CapabilityCard(
        id="macro_scan",
        required_nodes=("market_data", "news"),
        max_subagents=1,
        cost_estimate=3,
        spawn_role="Macro Analyst",
        preflight_prompt="Macro and news scan for XAUUSD. Summarize drivers only.",
    ),
    CapabilityCard(
        id="structure_review",
        required_nodes=("market_data", "structure", "liquidity", "supply_demand"),
        max_subagents=1,
        cost_estimate=3,
        spawn_role="Structure Analyst",
        preflight_prompt="Structure, liquidity, and supply/demand review for XAUUSD.",
    ),
    CapabilityCard(
        id="committee",
        required_nodes=FULL_ANALYSIS_NODES,
        max_subagents=5,
        cost_estimate=8,
        output_schema="team_briefing",
        team_preset="gold_analysis_committee",
    ),
    CapabilityCard(
        id="debate",
        required_nodes=FULL_ANALYSIS_NODES,
        max_subagents=3,
        cost_estimate=6,
        output_schema="team_briefing",
        team_preset="gold_debate_desk",
    ),
    CapabilityCard(
        id="gate_report",
        required_nodes=(),
        cost_estimate=1,
        output_schema="gate_report",
    ),
)

CARD_REGISTRY: dict[CapabilityId, CapabilityCard] = {card.id: card for card in _CARDS}


def get_card(card_id: str) -> CapabilityCard:
    try:
        return CARD_REGISTRY[card_id]
    except KeyError:
        raise KeyError(f"Unknown capability card: {card_id}") from None


def list_card_ids() -> tuple[str, ...]:
    return tuple(CARD_REGISTRY)
