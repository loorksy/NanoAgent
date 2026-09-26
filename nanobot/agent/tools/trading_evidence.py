"""Unified-loop evidence tool — registered only when LONORA_UNIFIED_LOOP is not off."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.schema import (
    ArraySchema,
    BooleanSchema,
    StringSchema,
    tool_parameters_schema,
)
from nanobot.trading.config import unified_loop_serving
from nanobot.trading.evidence.nodes import NODE_REGISTRY
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.unified_evidence import fetch_evidence_nodes

_NODE_IDS = tuple(sorted(NODE_REGISTRY))

_PARAMETERS = tool_parameters_schema(
    nodes=ArraySchema(
        StringSchema("Evidence node id", enum=list(_NODE_IDS)),
        description="Evidence nodes to fetch (market_data, structure, news, ...)",
        min_items=1,
    ),
    interval=StringSchema(
        "Candle interval (default 15m)",
        enum=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
    ),
    refresh=BooleanSchema(description="Re-run nodes even if already fetched this turn"),
    required=["nodes"],
)


@tool_parameters(_PARAMETERS)
class FetchEvidenceTool(Tool):
    """Fetch Evidence Nodes into the turn-scoped PipelineContext."""

    _scopes = {"core", "subagent"}

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool:
        return unified_loop_serving()

    @property
    def name(self) -> str:
        return "fetch_evidence"

    @property
    def description(self) -> str:
        return (
            "Fetch gold (XAUUSD) evidence nodes into this turn's pipeline. "
            f"Allowed nodes: {', '.join(_NODE_IDS)}. "
            "Use a subset for price or structure questions. "
            "Call run_trading_kernel only when the operator wants a recommendation. "
            "Returns evidence JSON only — never a BUY/SELL decision."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        nodes: list[str],
        interval: str = "15m",
        refresh: bool = False,
        **kwargs: Any,
    ) -> str:
        try:
            payload = await fetch_evidence_nodes(
                nodes,
                interval=interval,
                refresh=refresh,
            )
        except Exception as exc:
            return ToolResult.error(str(exc))
        payload["symbol"] = DATA_SYMBOL
        return json.dumps(payload, indent=2, default=str)
