"""Evidence tool — fetches evidence nodes into the turn-scoped pipeline context."""

from __future__ import annotations

from typing import Any

from mokli.agent.tools.base import Tool, ToolResult, tool_parameters
from mokli.agent.tools.schema import (
    ArraySchema,
    BooleanSchema,
    StringSchema,
    tool_parameters_schema,
)
from mokli.trading.evidence.nodes import NODE_REGISTRY
from mokli.trading.gold import DATA_SYMBOL
from mokli.trading.tool_errors import model_json
from mokli.trading.unified_evidence import fetch_evidence_nodes

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
        return model_json(payload)
