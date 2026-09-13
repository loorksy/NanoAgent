"""Default evidence graph — mirrors legacy orchestrator layer ordering."""

from __future__ import annotations

from dataclasses import dataclass

# Serial layers; nodes within a layer execute concurrently.
DEFAULT_ANALYSIS_LAYERS: tuple[tuple[str, ...], ...] = (
    ("market_data",),
    ("structure", "liquidity", "supply_demand", "multi_timeframe"),
    ("news",),
    ("geometry",),
    ("risk",),
    ("visual_capture",),
)


@dataclass(frozen=True)
class EvidenceGraph:
    """Named graph of evidence node layers."""

    name: str
    layers: tuple[tuple[str, ...], ...]

    def node_ids(self) -> frozenset[str]:
        ids: set[str] = set()
        for layer in self.layers:
            ids.update(layer)
        return frozenset(ids)


DEFAULT_ANALYSIS_GRAPH = EvidenceGraph(
    name="full_analysis",
    layers=DEFAULT_ANALYSIS_LAYERS,
)
