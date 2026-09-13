"""Named evidence node sets for turn planning."""

from __future__ import annotations

from nanobot.trading.evidence.graph import DEFAULT_ANALYSIS_GRAPH

FULL_ANALYSIS_NODES: tuple[str, ...] = tuple(sorted(DEFAULT_ANALYSIS_GRAPH.node_ids()))
MARKET_DATA_NODES: tuple[str, ...] = ("market_data",)
EMPTY_NODES: tuple[str, ...] = ()

# Minimum evidence required before the synthesizer may run.
SYNTHESIS_REQUIRED_NODES: frozenset[str] = frozenset(
    {
        "market_data",
        "structure",
        "liquidity",
        "supply_demand",
        "multi_timeframe",
        "news",
        "geometry",
        "risk",
    }
)

_SYNTHESIS_MODES = frozenset({"full_analysis", "team_swarm", "reevaluation"})


def mode_requires_synthesis(mode: str) -> bool:
    return mode in _SYNTHESIS_MODES
