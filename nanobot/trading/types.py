"""Trading pipeline wire types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TrendLabel = Literal["uptrend", "downtrend", "range", "unknown"]
Bias = Literal["bullish", "bearish", "neutral", "unknown"]
GateId = Literal["G1", "G2", "G3", "G4", "G6", "G7"]
GateStatus = Literal["pass", "veto", "unavailable"]
Decision = Literal["buy", "sell", "wait"]
PlanType = Literal["immediate", "anticipatory", "conditional"]
ExecutionState = Literal[
    "valid_now", "awaiting_activation", "expired", "invalidated", "blocked"
]


@dataclass
class PriceLevel:
    price: float
    time: int


@dataclass
class Swing:
    type: Literal["high", "low"]
    time: int
    price: float


@dataclass
class SupplyDemandZone:
    type: Literal["supply", "demand"]
    low: float
    high: float
    time: int


@dataclass
class StructureEvent:
    type: Literal["BOS", "CHoCH", "MSS"]
    direction: Literal["bullish", "bearish"]
    broken_level: float
    break_candle_time: int
    confirmation_close: float
    strength: float
    source: Literal["swing", "internal", "htf"] = "swing"


@dataclass
class LiquiditySweep:
    side: Literal["buy_side", "sell_side"]
    swept_level: float
    candle_time: int
    wick_extreme: float
    close_back_inside: bool
    strength: float
    followed_by_structure_shift: bool = False


@dataclass
class EconomicEvent:
    title: str
    time: str
    impact: Literal["low", "medium", "high"]
    currency: str | None = None


@dataclass
class Candle:
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    complete: bool = True


@dataclass
class MarketSync:
    ok: bool
    reason: str = ""
    gapped: bool = False


@dataclass
class AgentMarketContext:
    symbol: str
    interval: str
    candles: list[Candle]
    last_close: float
    atr: float
    sync: MarketSync
    quote_mid: float | None = None


@dataclass
class StructureResult:
    trend: TrendLabel
    swings: list[Swing]
    support: list[PriceLevel]
    resistance: list[PriceLevel]
    structure_events: list[StructureEvent]
    latest_structure_event: StructureEvent | None = None


@dataclass
class LiquidityResult:
    equal_highs: list[PriceLevel]
    equal_lows: list[PriceLevel]
    nearest_buy_side: PriceLevel | None
    nearest_sell_side: PriceLevel | None
    sweeps: list[LiquiditySweep]
    latest_sweep: LiquiditySweep | None = None


@dataclass
class SupplyDemandResult:
    zones: list[SupplyDemandZone]
    nearest_demand: SupplyDemandZone | None
    nearest_supply: SupplyDemandZone | None


@dataclass
class MultiTimeframeResult:
    current_bias: Bias
    higher_bias: Bias
    daily_bias: Bias
    conflict: bool


@dataclass
class NewsMacroResult:
    news_risk: Literal["low", "medium", "high", "unknown"]
    bias_impact: Literal["bullish", "bearish", "mixed", "unknown"]
    affected_currencies: list[str]
    upcoming_events: list[EconomicEvent]
    trade_allowed: bool
    reason: str


@dataclass
class TradeCandidate:
    id: str
    action: Decision
    entry: float
    entry_type: str
    stop_loss: float
    targets: list[float]
    rr: float
    quality_score: float
    setup_type: str = "structure"


@dataclass
class TradeValidationResult:
    accepted: bool
    reasons: list[str]
    warnings: list[str] = field(default_factory=list)
    rr: float | None = None


@dataclass
class RiskAgentResult:
    proposed_trade: TradeCandidate
    validation: TradeValidationResult
    account_warnings: list[str] = field(default_factory=list)
    selected_candidate: TradeCandidate | None = None
    candidates: list[TradeCandidate] = field(default_factory=list)


@dataclass
class EntryPlan:
    direction: Literal["buy", "sell"]
    entry_type: str
    entry: float
    stop_loss: float
    targets: list[float]
    activation_rule: dict[str, Any] | None = None
    min_rr: float | None = None


@dataclass
class GateVerdict:
    id: GateId
    name: str
    status: GateStatus
    reason: str = ""
    reason_ar: str = ""
    evidence: dict[str, Any] | None = None
    confidence_delta: int = 0
    started_at: int = 0
    finished_at: int = 0


@dataclass
class GateChainResult:
    verdicts: list[GateVerdict]
    allowed: bool
    confidence_delta: int
    vetoed_by: GateVerdict | None = None


@dataclass
class EntryZone:
    low: float
    high: float


@dataclass
class ScenarioWaypoint:
    bars_ahead: int
    price: float
    label: str = ""


@dataclass
class TimeframeRoles:
    lead: str = "15m"
    context: str = "4h"
    timing: str = "5m"


@dataclass
class DecisionHypothesis:
    scenario: str
    supporting: list[str] = field(default_factory=list)
    opposing: list[str] = field(default_factory=list)


@dataclass
class DecisionTrace:
    hypotheses: list[DecisionHypothesis] = field(default_factory=list)
    chosen_because: str = ""
    plan_type_because: str = ""


@dataclass
class VisualReview:
    state: Literal["checked", "not_checked", "partial"] = "not_checked"
    requested: list[str] = field(default_factory=list)
    captured: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class EvidenceSnapshot:
    payload: dict[str, Any] = field(default_factory=dict)
    evidence_levels: list[float] = field(default_factory=list)


@dataclass
class AgentRecommendation:
    action: Decision
    plan_type: PlanType | None = None
    execution_state: ExecutionState | None = None
    entry: float | None = None
    entry_type: str | None = None
    entry_zone: EntryZone | None = None
    stop_loss: float | None = None
    targets: list[float] = field(default_factory=list)
    take_profit: float | None = None
    activation_condition: str | None = None
    activation_rule: dict[str, Any] | None = None
    invalidation_rule: str | None = None
    invalidation_level: float | None = None
    alternative_scenario: str | None = None
    validity_candles: int | None = None
    timeframe_roles: TimeframeRoles | None = None
    decision_trace: DecisionTrace | None = None
    scenario_path: list[ScenarioWaypoint] = field(default_factory=list)
    alternative_scenario_path: list[ScenarioWaypoint] = field(default_factory=list)
    rr: float | None = None
    net_rr: float | None = None
    anchor_time: int | None = None
    symbol: str = "XAUUSD"
    interval: str = "15m"


@dataclass
class FinalDecisionResult:
    decision: Decision
    confidence: float
    summary: str
    key_reasons: list[str]
    risk_warnings: list[str]
    recommendation: AgentRecommendation
    plan_type: PlanType | None = None
    execution_state: ExecutionState | None = None
    public_reasoning_summary: list[str] = field(default_factory=list)
    gate_chain: GateChainResult | None = None
    refusal_summary: str | None = None
    visual_review: VisualReview | None = None
    evidence_snapshot: EvidenceSnapshot | None = None
    team_briefing: str | None = None
    artifacts_requested: list[str] = field(default_factory=list)


@dataclass
class ChartDrawing:
    type: str
    confidence: int
    label: str
    color: str
    style: str = "solid"
    fill: bool = False
    semantic_role: str = ""
    points: list[dict[str, float]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentFinalResult:
    decision: FinalDecisionResult
    structure: StructureResult | None = None
    liquidity: LiquidityResult | None = None
    supply_demand: SupplyDemandResult | None = None
    mtf: MultiTimeframeResult | None = None
    news: NewsMacroResult | None = None
    risk: RiskAgentResult | None = None
    market: AgentMarketContext | None = None
    drawings: list[ChartDrawing] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    recommendation_id: str | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)
    team_mode: str = "core"
    team_agents: list[dict[str, Any]] = field(default_factory=list)
    macro_drivers: list[dict[str, Any]] = field(default_factory=list)
    visual_snapshots: list[dict[str, Any]] = field(default_factory=list)
