"""Evidence graph runtime — Phase H of the Lonora hybrid architecture."""

from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.evidence.executor import run_evidence_graph, stage_sequence_from_graph
from nanobot.trading.evidence.graph import DEFAULT_ANALYSIS_GRAPH, EvidenceGraph, graph_for_nodes
from nanobot.trading.evidence.node_sets import (
    EMPTY_NODES,
    FULL_ANALYSIS_NODES,
    MARKET_DATA_NODES,
    SYNTHESIS_REQUIRED_NODES,
    mode_requires_synthesis,
)
from nanobot.trading.evidence.nodes import NODE_REGISTRY, EvidenceNode, get_node

__all__ = [
    "DEFAULT_ANALYSIS_GRAPH",
    "EMPTY_NODES",
    "EvidenceGraph",
    "EvidenceNode",
    "FULL_ANALYSIS_NODES",
    "MARKET_DATA_NODES",
    "NODE_REGISTRY",
    "PipelineContext",
    "SYNTHESIS_REQUIRED_NODES",
    "get_node",
    "graph_for_nodes",
    "mode_requires_synthesis",
    "run_evidence_graph",
    "stage_sequence_from_graph",
]
