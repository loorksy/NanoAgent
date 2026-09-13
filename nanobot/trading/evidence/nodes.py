"""Evidence Node definitions — one unit of analysis per node."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar

from nanobot.trading.agents.liquidity import run_liquidity_agent
from nanobot.trading.agents.market_data import run_market_data_agent
from nanobot.trading.agents.multi_timeframe import run_multi_timeframe_agent
from nanobot.trading.agents.news_macro import run_news_macro_agent
from nanobot.trading.agents.risk import run_risk_agent
from nanobot.trading.agents.structure import run_structure_agent
from nanobot.trading.agents.supply_demand import run_supply_demand_agent
from nanobot.trading.agents.visual_capture import capture_visual_evidence
from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.geometry.snapshot import build_geometry_snapshot


class EvidenceNode(ABC):
    """Atomic evidence producer in the analysis DAG."""

    id: ClassVar[str]
    stage: ClassVar[str | None]
    depends_on: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> None:
        """Run this node and write outputs onto ``ctx``."""


class MarketDataNode(EvidenceNode):
    id = "market_data"
    stage = "market_data"

    async def execute(self, ctx: PipelineContext) -> None:
        ctx.market = await asyncio.to_thread(run_market_data_agent, ctx.symbol, ctx.interval)
        if ctx.market is not None and not ctx.market.sync.ok:
            ctx.market_sync_failed = True
            ctx.aborted = True
            ctx.abort_reason = ctx.market.sync.reason or "Market data sync failed"


class StructureNode(EvidenceNode):
    id = "structure"
    stage = "structure"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.market is not None
        ctx.structure = await asyncio.to_thread(run_structure_agent, ctx.market)


class LiquidityNode(EvidenceNode):
    id = "liquidity"
    stage = "liquidity"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.market is not None
        ctx.liquidity = await asyncio.to_thread(run_liquidity_agent, ctx.market)


class SupplyDemandNode(EvidenceNode):
    id = "supply_demand"
    stage = "supply_demand"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.market is not None
        ctx.supply_demand = await asyncio.to_thread(run_supply_demand_agent, ctx.market)


class MultiTimeframeNode(EvidenceNode):
    id = "multi_timeframe"
    stage = "multi_timeframe"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.market is not None
        ctx.mtf = await asyncio.to_thread(run_multi_timeframe_agent, ctx.market)


class NewsNode(EvidenceNode):
    id = "news"
    stage = "news"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        ctx.news = await asyncio.to_thread(run_news_macro_agent)


class GeometryNode(EvidenceNode):
    id = "geometry"
    stage = None
    depends_on = ("structure",)

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.structure is not None
        ctx.geometry = build_geometry_snapshot(ctx.structure)


class RiskNode(EvidenceNode):
    id = "risk"
    stage = "risk"
    depends_on = ("market_data", "structure", "supply_demand")

    async def execute(self, ctx: PipelineContext) -> None:
        assert ctx.market is not None
        assert ctx.structure is not None
        assert ctx.supply_demand is not None
        ctx.risk = await asyncio.to_thread(
            run_risk_agent,
            ctx.market,
            ctx.structure,
            ctx.supply_demand,
        )


class VisualCaptureNode(EvidenceNode):
    id = "visual_capture"
    stage = "research"
    depends_on = ("market_data",)

    async def execute(self, ctx: PipelineContext) -> None:
        visual, snapshots = await capture_visual_evidence(
            ctx.interval,
            capture=ctx.visual_capture,
        )
        ctx.visual = visual
        ctx.snapshots = snapshots


_ALL_NODES: tuple[EvidenceNode, ...] = (
    MarketDataNode(),
    StructureNode(),
    LiquidityNode(),
    SupplyDemandNode(),
    MultiTimeframeNode(),
    NewsNode(),
    GeometryNode(),
    RiskNode(),
    VisualCaptureNode(),
)

NODE_REGISTRY: dict[str, EvidenceNode] = {node.id: node for node in _ALL_NODES}


def get_node(node_id: str) -> EvidenceNode:
    try:
        return NODE_REGISTRY[node_id]
    except KeyError:
        raise KeyError(f"Unknown evidence node: {node_id}") from None
