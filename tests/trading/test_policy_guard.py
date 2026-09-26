"""Tests for the evidence graph helpers used by the Policy Guard."""

from nanobot.trading.evidence import graph_for_nodes


def test_graph_for_nodes_filters_layers() -> None:
    graph = graph_for_nodes(frozenset({"market_data", "news"}))
    assert graph.layers == (("market_data",), ("news",))
