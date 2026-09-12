import asyncio

from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.reprice_loop import apply_g7_reprice_loop
from nanobot.trading.types import (
    AgentRecommendation,
    EntryPlan,
    GateChainResult,
    GateVerdict,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    StructureResult,
    SupplyDemandResult,
)


def _minimal_inputs(plan: EntryPlan) -> GateInputs:
    return GateInputs(
        now_ms=1_700_000_000_000,
        news=NewsMacroResult(
            news_risk="low",
            bias_impact="mixed",
            affected_currencies=["USD"],
            upcoming_events=[],
            trade_allowed=True,
            reason="",
        ),
        structure=StructureResult(
            trend="bullish",
            swings=[],
            support=[],
            resistance=[],
            structure_events=[],
        ),
        liquidity=LiquidityResult(
            equal_highs=[],
            equal_lows=[],
            nearest_buy_side=None,
            nearest_sell_side=None,
            sweeps=[],
        ),
        supply_demand=SupplyDemandResult(
            zones=[],
            nearest_demand=None,
            nearest_supply=None,
        ),
        mtf=MultiTimeframeResult(
            current_bias="bullish",
            higher_bias="bullish",
            daily_bias="bullish",
            conflict=False,
        ),
        plan=plan,
        atr=5.0,
        visual_timeframes=["15m"],
        fetch_live_price=lambda: 2405.0,
    )


def test_reprice_loop_updates_entry_after_g7_reanchor() -> None:
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2400.0,
        stop_loss=2390.0,
        targets=[2410.0, 2420.0],
    )
    rec = AgentRecommendation(action="buy", entry=2400.0, stop_loss=2390.0, targets=[2410.0])
    gates = build_gates(_minimal_inputs(plan))
    initial = GateChainResult(
        verdicts=[
            GateVerdict(
                id="G7",
                name="Live revalidation",
                status="pass",
                reason_ar="Reanchored",
                evidence={"reanchored_entry": 2405.0},
                confidence_delta=-5,
                started_at=1,
                finished_at=2,
            )
        ],
        allowed=True,
        confidence_delta=-5,
        vetoed_by=None,
    )
    chain, updated_plan, updated_rec = asyncio.run(
        apply_g7_reprice_loop(initial, gates, plan, rec)
    )
    assert updated_plan.entry == 2405.0
    assert updated_rec.entry == 2405.0
    assert any(v.id == "G6" for v in chain.verdicts)
