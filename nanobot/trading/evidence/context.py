"""Mutable pipeline context passed through Evidence Node execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nanobot.trading.types import (
    AgentMarketContext,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    VisualReview,
)


@dataclass
class PipelineContext:
    """Intermediate state for one analysis run through the evidence graph."""

    symbol: str
    interval: str
    visual_capture: Any | None = None

    market: AgentMarketContext | None = None
    structure: StructureResult | None = None
    liquidity: LiquidityResult | None = None
    supply_demand: SupplyDemandResult | None = None
    mtf: MultiTimeframeResult | None = None
    news: NewsMacroResult | None = None
    geometry: dict[str, Any] | None = None
    risk: RiskAgentResult | None = None
    visual: VisualReview | None = None
    snapshots: list[dict[str, Any]] = field(default_factory=list)

    market_sync_failed: bool = False
    aborted: bool = False
    abort_reason: str = ""
