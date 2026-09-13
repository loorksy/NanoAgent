from nanobot.trading.gates.plan_alignment import (
    evaluate_liquidity_alignment,
    evaluate_supply_demand_alignment,
)
from nanobot.trading.types import (
    EntryPlan,
    LiquidityResult,
    LiquiditySweep,
    PriceLevel,
    SupplyDemandResult,
    SupplyDemandZone,
)


def test_g2_vetoes_buy_into_overhead_liquidity() -> None:
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2665.0],
    )
    liquidity = LiquidityResult(
        equal_highs=[PriceLevel(price=2651.0, time=1)],
        equal_lows=[],
        nearest_buy_side=PriceLevel(price=2651.0, time=1),
        nearest_sell_side=None,
        sweeps=[],
    )
    status, reason = evaluate_liquidity_alignment(plan, liquidity, atr=5.0)
    assert status == "veto"
    assert reason


def test_g3_vetoes_buy_inside_supply_zone() -> None:
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2665.0],
    )
    supply_demand = SupplyDemandResult(
        zones=[
            SupplyDemandZone(type="supply", low=2648.0, high=2652.0, time=1),
        ],
        nearest_demand=None,
        nearest_supply=SupplyDemandZone(type="supply", low=2648.0, high=2652.0, time=1),
    )
    status, reason = evaluate_supply_demand_alignment(plan, supply_demand, locale="ar")
    assert status == "veto"
    assert "عرض" in reason


def test_g2_passes_when_liquidity_clear() -> None:
    plan = EntryPlan(
        direction="sell",
        entry_type="market",
        entry=2650.0,
        stop_loss=2660.0,
        targets=[2635.0],
    )
    liquidity = LiquidityResult(
        equal_highs=[],
        equal_lows=[PriceLevel(price=2620.0, time=1)],
        nearest_buy_side=PriceLevel(price=2670.0, time=1),
        nearest_sell_side=PriceLevel(price=2620.0, time=1),
        sweeps=[
            LiquiditySweep(
                side="sell_side",
                swept_level=2620.0,
                candle_time=1,
                wick_extreme=2618.0,
                close_back_inside=False,
                strength=0.5,
            )
        ],
        latest_sweep=None,
    )
    status, _ = evaluate_liquidity_alignment(plan, liquidity, atr=5.0)
    assert status == "pass"
