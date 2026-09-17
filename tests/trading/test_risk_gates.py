"""Unit tests for deterministic risk / news / execution gates."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.gates.adr_gap import evaluate_adr_chase, evaluate_gap_chase, gap_points
from nanobot.trading.gates.bad_tick import evaluate_bad_tick
from nanobot.trading.gates.build_gates import GateInputs, build_gates
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.gates.cooldown_lock import evaluate_cooldown_lock
from nanobot.trading.gates.drawdown_breaker import (
    evaluate_drawdown_breaker,
    flatten_required_reason,
)
from nanobot.trading.gates.execution import collect_execution_checks, first_blocker
from nanobot.trading.gates.margin_guard import evaluate_margin_guard
from nanobot.trading.gates.max_positions import evaluate_max_positions, evaluate_no_martingale
from nanobot.trading.gates.news_candle import evaluate_news_candle_shield, is_news_candle
from nanobot.trading.gates.news_operational import evaluate_news_operational
from nanobot.trading.gates.news_window import evaluate_news_window
from nanobot.trading.gates.pending_ttl import evaluate_pending_ttl
from nanobot.trading.gates.position_sizing import evaluate_position_sizing, lot_from_balance
from nanobot.trading.gates.proposal_bracket import evaluate_confirm_slippage, evaluate_proposal_ttl
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.gates.rr_filter import evaluate_rr_filter, farthest_rr
from nanobot.trading.gates.session_lock import evaluate_session_lock
from nanobot.trading.gates.slippage_guard import evaluate_slippage_guard
from nanobot.trading.gates.spread_guard import evaluate_spread_guard
from nanobot.trading.gates.stale_quote import evaluate_stale_quote
from nanobot.trading.gates.time_stop import evaluate_time_stop
from nanobot.trading.gates.trade_management import (
    overnight_stop,
    partial_close_fraction,
    should_move_to_breakeven,
    trailing_stop,
)
from nanobot.trading.policy import (
    BAD_TICK_POINTS,
    DAILY_DRAWDOWN_PCT,
    GOLD_POINT,
    MARGIN_MIN_PCT,
    MAX_OPEN_GOLD_POSITIONS,
    MIN_RR,
    PROPOSAL_TTL_SECONDS,
    RISK_PCT_DEFAULT,
    SLIPPAGE_MAX_POINTS,
    SPREAD_MAX_POINTS,
    STALE_QUOTE_SECONDS,
)
from nanobot.trading.types import EconomicEvent, EntryPlan, VisualReview


def _plan(rr: float = 2.5) -> EntryPlan:
    entry = 2650.0
    stop = 2640.0
    target = entry + (entry - stop) * rr
    return EntryPlan(
        direction="buy",
        entry_type="market",
        entry=entry,
        stop_loss=stop,
        targets=[target],
    )


def _noon_ms() -> int:
    return int(datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp() * 1000)


def test_rr_filter_blocks_below_minimum():
    plan = _plan(1.5)
    assert farthest_rr(plan) < MIN_RR
    check = evaluate_rr_filter(plan)
    assert check.status == "veto"


def test_rr_filter_passes_at_two_to_one():
    plan = _plan(2.0)
    assert evaluate_rr_filter(plan).status == "pass"


def test_rr_live_fill_blocks_when_degraded():
    plan = _plan(2.0)
    # Fill one point worse: entry 2650.01, stop 2640 → RR to 2670 is 19.99/10.01 < 2 but still > 1.5
    # Push live entry far enough that RR < 1.5
    check = evaluate_rr_filter(plan, live_entry=2654.0)
    assert check.status == "veto"


def test_spread_guard_blocks_wide_spread():
    risk = RiskSnapshot(spread_points=SPREAD_MAX_POINTS + 1)
    assert evaluate_spread_guard(risk).status == "veto"
    assert evaluate_spread_guard(RiskSnapshot(spread_points=20)).status == "pass"


def test_spread_guard_pre_news_multiplier():
    risk = RiskSnapshot(
        spread_points=45,
        normal_spread_points=10,
        minutes_to_high_impact=1.0,
    )
    assert evaluate_spread_guard(risk).status == "veto"


def test_cooldown_lock_blocks_while_active():
    now = _noon_ms()
    risk = RiskSnapshot(cooldown_until_ms=now + 60_000, cooldown_reason="two_consecutive_losses")
    assert evaluate_cooldown_lock(risk, now_ms=now).status == "veto"
    assert evaluate_cooldown_lock(RiskSnapshot(cooldown_until_ms=now - 1), now_ms=now).status == "pass"


def test_max_positions_cap():
    plan = _plan()
    risk = RiskSnapshot(open_positions=MAX_OPEN_GOLD_POSITIONS)
    assert evaluate_max_positions(plan, risk).status == "veto"
    assert evaluate_max_positions(plan, RiskSnapshot(open_positions=0)).status == "pass"


def test_no_double_losing_side():
    plan = _plan()
    risk = RiskSnapshot(open_positions=1, open_buy_losing=True)
    assert evaluate_max_positions(plan, risk).status == "veto"


def test_no_martingale():
    assert evaluate_no_martingale(adding_to_loser=True).status == "veto"
    assert evaluate_no_martingale(adding_to_loser=False).status == "pass"


def test_drawdown_breaker_and_kill_switch():
    limit = DAILY_DRAWDOWN_PCT
    assert evaluate_drawdown_breaker(RiskSnapshot(daily_drawdown_pct=limit)).status == "veto"
    assert evaluate_drawdown_breaker(RiskSnapshot(kill_switch=True)).status == "veto"
    assert evaluate_drawdown_breaker(RiskSnapshot(daily_drawdown_pct=0.01)).status == "pass"
    assert flatten_required_reason(RiskSnapshot(kill_switch=True)) == "kill_switch"
    assert flatten_required_reason(RiskSnapshot(emergency_lock=True)) == "emergency_lock"
    assert flatten_required_reason(RiskSnapshot(daily_drawdown_pct=limit)) == "daily_drawdown"
    assert flatten_required_reason(RiskSnapshot(daily_drawdown_pct=0.01)) is None


def test_equity_spike_breaker():
    assert evaluate_drawdown_breaker(RiskSnapshot(equity_spike_pct=0.02)).status == "veto"


def test_position_sizing_dual_check():
    plan = _plan()
    expected = lot_from_balance(10_000, plan.entry, plan.stop_loss, risk_pct=RISK_PCT_DEFAULT)
    assert expected > 0
    ok = evaluate_position_sizing(plan, RiskSnapshot(account_balance=10_000, proposed_lot=expected))
    assert ok.status == "pass"
    bad = evaluate_position_sizing(plan, RiskSnapshot(account_balance=10_000, proposed_lot=expected * 5))
    assert bad.status == "veto"


def test_stale_quote():
    assert evaluate_stale_quote(RiskSnapshot(quote_age_seconds=STALE_QUOTE_SECONDS + 1)).status == "veto"
    assert evaluate_stale_quote(RiskSnapshot(quote_age_seconds=1)).status == "pass"


def test_pending_ttl_and_half_distance():
    now = _noon_ms()
    plan = _plan(2.0)
    old = RiskSnapshot(pending_created_ms=now - 4 * 3_600_000)
    assert evaluate_pending_ttl(plan, old, now_ms=now).status == "veto"
    ran = RiskSnapshot(pending_created_ms=now)
    # Target is 20 above entry; half is 10. Live 2660 is 10 above 2650.
    live = plan.entry + abs(plan.targets[0] - plan.entry) * 0.5
    assert evaluate_pending_ttl(plan, ran, now_ms=now, live_price=live).status == "veto"


def test_pending_cancel_before_news():
    now = _noon_ms()
    plan = _plan()
    risk = RiskSnapshot(pending_created_ms=now, minutes_to_high_impact=5)
    assert evaluate_pending_ttl(plan, risk, now_ms=now).status == "veto"


def test_session_midnight_and_holiday():
    midnight = int(datetime(2023, 11, 15, 23, 58, tzinfo=UTC).timestamp() * 1000)
    assert evaluate_session_lock(None, now_ms=midnight).status == "veto"
    nye = int(datetime(2024, 1, 1, 12, 0, tzinfo=UTC).timestamp() * 1000)
    assert evaluate_session_lock(None, now_ms=nye).status == "veto"
    assert evaluate_session_lock(None, now_ms=_noon_ms()).status == "pass"


def test_session_rollover_only_near_news():
    top = int(datetime(2023, 11, 15, 14, 0, tzinfo=UTC).timestamp() * 1000)
    assert evaluate_session_lock(None, now_ms=top).status == "pass"
    news = RiskSnapshot(news_day=True)
    assert evaluate_session_lock(news, now_ms=top).status == "veto"


def test_bad_tick():
    last = 2650.0
    spike = last + (BAD_TICK_POINTS * GOLD_POINT)
    assert evaluate_bad_tick(RiskSnapshot(last_mid=last, current_mid=spike)).status == "veto"
    assert evaluate_bad_tick(RiskSnapshot(last_mid=last, current_mid=last + 0.10)).status == "pass"


def test_news_operational_freeze_and_void():
    plan = _plan()
    assert evaluate_news_operational(plan, RiskSnapshot(minutes_to_high_impact=10)).status == "veto"
    assert evaluate_news_operational(plan, RiskSnapshot(seconds_since_high_impact=10)).status == "veto"
    assert evaluate_news_operational(plan, RiskSnapshot(minutes_since_high_impact=5)).status == "veto"
    assert evaluate_news_operational(plan, RiskSnapshot(minutes_to_high_impact=45)).status == "pass"


def test_margin_and_slippage():
    assert evaluate_margin_guard(RiskSnapshot(margin_level_pct=MARGIN_MIN_PCT - 1)).status == "veto"
    assert evaluate_slippage_guard(RiskSnapshot(expected_slippage_points=SLIPPAGE_MAX_POINTS + 1)).status == "veto"
    assert evaluate_slippage_guard(RiskSnapshot(exec_latency_ms=1500)).status == "veto"


def test_news_candle_and_emergency_burst():
    assert is_news_candle(candle_range=6.0, atr=1.0) is True
    assert evaluate_news_candle_shield(candle_range=6.0, atr=1.0).status == "veto"
    assert evaluate_news_candle_shield(candle_range=1.0, atr=1.0, points_last_minute=80).status == "veto"


def test_adr_and_gap_chase():
    assert evaluate_adr_chase(session_range=40.0, adr=20.0).status == "veto"
    assert evaluate_gap_chase(gap_points=150).status == "veto"
    assert gap_points(2651.5, 2650.0) == pytest.approx(150.0)


def test_proposal_bracket_ttl_and_slippage():
    now = 1_000_000
    assert evaluate_proposal_ttl(created_ms=now - int((PROPOSAL_TTL_SECONDS + 1) * 1000), now_ms=now).status == "veto"
    assert evaluate_confirm_slippage(proposed_price=2650.0, live_price=2650.40).status == "veto"
    assert evaluate_confirm_slippage(proposed_price=2650.0, live_price=2650.05).status == "pass"


def test_time_stop_and_overnight_buffer():
    now = _noon_ms()
    open_ms = now - 4 * 3_600_000
    assert evaluate_time_stop(open_ms=open_ms, now_ms=now, favorable_progress=False).status == "veto"
    assert evaluate_time_stop(open_ms=open_ms, now_ms=now, favorable_progress=True).status == "pass"
    plan = _plan()
    wider = overnight_stop(plan)
    assert wider < plan.stop_loss


def test_trade_management_helpers():
    plan = _plan(2.0)
    assert should_move_to_breakeven(plan, 2660.0) is True
    assert should_move_to_breakeven(plan, 2651.0) is False
    trail = trailing_stop(plan, 2665.0, atr=2.0)
    assert trail > plan.stop_loss
    assert partial_close_fraction(plan, plan.targets[0]) == pytest.approx(0.5)


def test_news_window_still_blocks_thirty_minutes_before():
    events = [EconomicEvent(title="NFP", time="2023-11-15T12:20:00+00:00", impact="high")]
    now = int(datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp() * 1000)
    assert evaluate_news_window(events, now).blocked is True


def test_hitl_blocker_without_operator_confirm():
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        RiskSnapshot(),
        now_ms=_noon_ms(),
        operator_confirmed=False,
    )
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "hitl"


def test_hitl_passes_when_operator_confirmed_and_clean():
    plan = _plan()
    risk = RiskSnapshot(
        spread_points=20,
        quote_age_seconds=1,
        last_mid=2650.0,
        current_mid=2650.1,
        account_balance=10_000,
        proposed_lot=lot_from_balance(10_000, plan.entry, plan.stop_loss),
        margin_level_pct=800,
    )
    checks = collect_execution_checks(
        plan,
        risk,
        now_ms=_noon_ms(),
        operator_confirmed=True,
        proposal_created_ms=_noon_ms(),
        proposed_price=plan.entry,
        live_price=plan.entry,
    )
    assert first_blocker(checks) is None


def test_operator_toggle_is_disabled_by_operator_not_silent_pass():
    plan = _plan(1.0)
    risk = RiskSnapshot(feature_toggles={"rr_filter": False})
    checks = collect_execution_checks(plan, risk, now_ms=_noon_ms(), operator_confirmed=True)
    rr = dict(checks)["rr"]
    assert rr.status == "pass"
    assert rr.evidence.get("disabled_by_operator") is True
    assert rr.reason_key == "gate.disabled_by_operator"


def test_stale_quote_toggle_cannot_bypass_integrity():
    risk = RiskSnapshot(
        quote_age_seconds=STALE_QUOTE_SECONDS + 5,
        feature_toggles={"stale_quote": False},
    )
    checks = collect_execution_checks(
        _plan(),
        risk,
        now_ms=_noon_ms(),
        operator_confirmed=True,
    )
    stale = dict(checks)["stale_quote"]
    assert stale.status == "veto"
    assert stale.evidence.get("disabled_by_operator") is not True


def test_hitl_toggle_cannot_bypass_confirm():
    checks = collect_execution_checks(
        _plan(),
        RiskSnapshot(feature_toggles={"hitl": False}),
        now_ms=_noon_ms(),
        operator_confirmed=False,
    )
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "hitl"


def test_time_stop_is_invoked_from_execution_path():
    plan = _plan()
    now = _noon_ms()
    stale_open = now - int(4 * 3_600_000)
    checks = collect_execution_checks(
        plan,
        RiskSnapshot(spread_points=20, quote_age_seconds=1, margin_level_pct=800),
        now_ms=now,
        operator_confirmed=True,
        position_open_ms=stale_open,
        favorable_progress=False,
    )
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "time_stop"


def test_widen_stop_is_blocked_from_execution_path():
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        RiskSnapshot(spread_points=20, quote_age_seconds=1, margin_level_pct=800),
        now_ms=_noon_ms(),
        operator_confirmed=True,
        current_stop=plan.stop_loss,
        requested_stop=plan.stop_loss - 5,
    )
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "no_widen"


@pytest.mark.asyncio
async def test_build_gates_includes_new_ids_and_rr_vetoes():
    weak = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2660.0],
    )
    from nanobot.trading.types import StructureResult

    structure = StructureResult(
        trend="uptrend",
        swings=[],
        support=[],
        resistance=[],
        structure_events=[],
    )
    gates = build_gates(
        GateInputs(
            now_ms=_noon_ms(),
            news=None,
            structure=structure,
            liquidity=None,
            supply_demand=None,
            mtf=None,
            plan=weak,
            atr=5.0,
            visual=VisualReview(state="checked", captured=["15m"]),
            fetch_live_price=lambda: 2650.0,
        )
    )
    ids = [g.id for g in gates]
    for needed in ("G8", "G9", "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19", "G20"):
        assert needed in ids
    chain = await run_gate_chain(gates)
    assert chain.allowed is False
    assert chain.vetoed_by is not None
    assert chain.vetoed_by.id == "G8"
