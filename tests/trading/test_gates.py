import pytest

from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.gates.entry_semantics import validate_entry_coherence
from nanobot.trading.types import EntryPlan, VisualReview


def test_validate_entry_coherence_buy():
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2660.0, 2670.0],
    )
    ok, reasons = validate_entry_coherence(plan, atr=5.0)
    assert ok
    assert not reasons


@pytest.mark.asyncio
async def test_gate_chain_runs():
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2660.0],
    )
    gates = build_gates(
        GateInputs(
            now_ms=1_700_000_000_000,
            news=None,
            structure=None,
            liquidity=None,
            supply_demand=None,
            mtf=None,
            plan=plan,
            atr=5.0,
            visual=VisualReview(state="not_checked"),
            fetch_live_price=lambda: 2650.0,
        )
    )
    chain = await run_gate_chain(gates)
    assert chain.verdicts
    assert chain.allowed is False  # G4 structure unavailable (required)


@pytest.mark.asyncio
async def test_g4_visual_state_penalties():
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2660.0],
    )
    from nanobot.trading.types import StructureResult

    structure = StructureResult(
        trend="bullish",
        swings=[],
        support=[],
        resistance=[],
        structure_events=[],
    )

    async def _delta(visual: VisualReview) -> int:
        gates = build_gates(
            GateInputs(
                now_ms=1_700_000_000_000,
                news=None,
                structure=structure,
                liquidity=None,
                supply_demand=None,
                mtf=None,
                plan=plan,
                atr=5.0,
                visual=visual,
                fetch_live_price=lambda: 2650.0,
            )
        )
        g4 = next(g for g in gates if g.id == "G4")
        raw = await g4.run()
        return int(raw.get("confidence_delta", 0) or 0)

    assert await _delta(VisualReview(state="checked", captured=["15m"])) == 0
    assert await _delta(VisualReview(state="partial", captured=["15m"], missing=["1h"])) == -10
    assert await _delta(VisualReview(state="not_checked")) == -15
