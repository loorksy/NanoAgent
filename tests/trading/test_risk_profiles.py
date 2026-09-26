"""Risk-profile presets and slider derivations (04 §4.1–§4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mokli.config.loader import save_config
from mokli.config.schema import Config, TradingRiskParameters
from mokli.trading.gates.execution import collect_execution_checks, first_blocker
from mokli.trading.gates.position_sizing import lot_from_balance
from mokli.trading.gates.risk_snapshot import RiskSnapshot
from mokli.trading.policy import invalidate_live_cache, live
from mokli.trading.risk_profiles import (
    DERIVED_FIELDS,
    PRESET_NAMES,
    PROFILE_NAMES,
    PROFILES,
    SLIDER_FIELDS,
    SLIDER_RANGES,
    apply_profile,
    derive,
    derived_values,
    detect_profile,
    matches_preset,
    reference_lot,
)
from mokli.trading.types import EntryPlan

NOON_MS = 1_700_049_600_000  # 2023-11-15 12:00 UTC


def _assert_invariants(p: TradingRiskParameters) -> None:
    assert p.risk_pct_max >= p.risk_pct_default >= p.risk_pct_news_day > 0
    assert 0 < p.equity_spike_pct <= p.daily_drawdown_pct
    assert p.min_rr_live_fill <= p.min_rr
    assert p.breakeven_rr <= p.min_rr
    assert p.news_blackout_before_minutes >= p.pre_news_freeze_minutes >= p.news_shield_minutes
    assert p.news_blackout_after_minutes == p.news_shield_minutes
    assert p.post_news_entry_wait_minutes == p.news_shield_minutes
    assert 0 < p.spread_pre_news_minutes < p.news_shield_minutes
    assert p.cooldown_after_two_losses_session_minutes <= p.cooldown_after_two_losses_minutes
    assert p.cooldown_after_news_stop_minutes <= p.cooldown_after_two_losses_session_minutes
    assert p.cooldown_consecutive_losses == 2
    assert p.spread_multiplier_pre_news == 3.0
    assert 0 < p.flat_near_entry_points < p.spread_max_points
    if p.max_open_gold_positions > 0:
        assert p.max_total_lots >= reference_lot(p.risk_pct_default) * p.max_open_gold_positions - 1e-9
    else:
        assert p.max_total_lots == 0
    TradingRiskParameters.model_validate(p.model_dump())


def test_catalog_shapes() -> None:
    assert set(PROFILES) == set(PRESET_NAMES) == {"conservative", "balanced", "aggressive"}
    assert PROFILE_NAMES == (*PRESET_NAMES, "custom")
    assert len(SLIDER_FIELDS) == 7
    assert set(SLIDER_RANGES) == set(SLIDER_FIELDS)
    assert not set(SLIDER_FIELDS) & set(DERIVED_FIELDS)
    for name in (*SLIDER_FIELDS, *DERIVED_FIELDS):
        assert name in TradingRiskParameters.model_fields
    for preset in PROFILES.values():
        assert set(preset) == set(SLIDER_FIELDS)


@pytest.mark.parametrize(
    ("name", "risk", "daily", "positions", "rr", "news", "cooldown", "spread"),
    [
        ("conservative", 0.5, 2.0, 1, 2.5, 30.0, 240.0, 45.0),
        ("balanced", 1.0, 3.0, 2, 2.0, 15.0, 180.0, 60.0),
        ("aggressive", 2.0, 5.0, 3, 1.5, 10.0, 120.0, 80.0),
    ],
)
def test_presets_match_design_table(
    name: str,
    risk: float,
    daily: float,
    positions: int,
    rr: float,
    news: float,
    cooldown: float,
    spread: float,
) -> None:
    p = apply_profile(TradingRiskParameters(), name)
    assert p.risk_profile == name
    assert p.risk_pct_default == risk
    assert p.daily_drawdown_pct == daily
    assert p.max_open_gold_positions == positions
    assert p.min_rr == rr
    assert p.news_shield_minutes == news
    assert p.cooldown_after_two_losses_minutes == cooldown
    assert p.spread_max_points == spread
    assert matches_preset(p, name)
    assert detect_profile(p) == name


@pytest.mark.parametrize("name", PRESET_NAMES)
def test_every_preset_derives_valid_params_respecting_gate_invariants(name: str) -> None:
    p = apply_profile(TradingRiskParameters(), name)
    _assert_invariants(p)
    assert derive(p) == p


def test_balanced_derivation_values() -> None:
    p = apply_profile(TradingRiskParameters(), "balanced")
    assert p.risk_pct_max == 2.0
    assert p.risk_pct_news_day == 0.5
    assert p.equity_spike_pct == 2.01
    assert p.min_rr_live_fill == 1.5
    assert p.breakeven_rr == 1.0
    assert p.pre_news_freeze_minutes == 22.5
    assert p.news_blackout_before_minutes == 30.0
    assert p.spread_pre_news_minutes == 3.0
    assert p.cooldown_after_two_losses_session_minutes == 60.0
    assert p.cooldown_after_news_stop_minutes == 45.0
    assert p.flat_near_entry_points == 30.0
    assert reference_lot(1.0) == 0.2
    assert p.max_total_lots == 0.4


def _slider_grid() -> list[dict[str, float | int]]:
    combos: list[dict[str, float | int]] = []
    for risk in (0.25, 3.0):
        for daily in (1.0, 6.0):
            for positions in (1, 4):
                for rr in (1.5, 3.0):
                    for news in (5.0, 45.0):
                        for cooldown in (60.0, 360.0):
                            for spread in (30.0, 120.0):
                                combos.append(
                                    {
                                        "risk_pct_default": risk,
                                        "daily_drawdown_pct": daily,
                                        "max_open_gold_positions": positions,
                                        "min_rr": rr,
                                        "news_shield_minutes": news,
                                        "cooldown_after_two_losses_minutes": cooldown,
                                        "spread_max_points": spread,
                                    }
                                )
    return combos


def test_derive_holds_invariants_across_slider_extremes() -> None:
    for combo in _slider_grid():
        params = TradingRiskParameters.model_validate({**TradingRiskParameters().model_dump(), **combo})
        derived = derive(params)
        _assert_invariants(derived)
        for field in SLIDER_FIELDS:
            assert getattr(derived, field) == combo[field]


def test_derive_clamps_to_schema_bounds() -> None:
    params = TradingRiskParameters(risk_pct_default=80.0)
    derived = derive(params)
    assert derived.risk_pct_max == 100.0
    values = derived_values(TradingRiskParameters(min_rr=0.2))
    assert values["min_rr_live_fill"] == 0.0


def test_derive_zero_positions_means_no_total_cap() -> None:
    assert derive(TradingRiskParameters(max_open_gold_positions=0)).max_total_lots == 0.0


def test_apply_custom_only_tags_profile() -> None:
    base = TradingRiskParameters(min_rr=4.0, risk_profile="aggressive")
    out = apply_profile(base, "custom")
    assert out.risk_profile == "custom"
    assert out.min_rr == 4.0
    assert detect_profile(out) == "custom"


def test_apply_unknown_profile_raises() -> None:
    with pytest.raises(KeyError):
        apply_profile(TradingRiskParameters(), "yolo")


def test_reference_lot_edges() -> None:
    assert reference_lot(0) == 0.0
    assert reference_lot(-1) == 0.0
    assert reference_lot(0.01) == 0.01
    assert reference_lot(2.0) == 0.4


@pytest.mark.parametrize("name", PRESET_NAMES)
def test_preset_reaches_live_policy_and_clean_plan_passes_gates(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("mokli.config.loader._current_config_path", config_path)
    config = Config()
    config.trading_risk_parameters = apply_profile(config.trading_risk_parameters, name)
    save_config(config, config_path)
    invalidate_live_cache()
    policy = live()
    assert policy.MIN_RR == PROFILES[name]["min_rr"]
    assert policy.SPREAD_MAX_POINTS == PROFILES[name]["spread_max_points"]

    entry, stop = 2650.0, 2640.0
    plan = EntryPlan(
        direction="buy",
        entry_type="market",
        entry=entry,
        stop_loss=stop,
        targets=[entry + (entry - stop) * 3.0],
    )
    risk = RiskSnapshot(
        spread_points=20,
        quote_age_seconds=1,
        last_mid=entry,
        current_mid=entry,
        account_balance=10_000,
        proposed_lot=lot_from_balance(10_000, entry, stop),
        margin_level_pct=800,
    )
    checks = collect_execution_checks(
        plan,
        risk,
        now_ms=NOON_MS,
        operator_confirmed=True,
        proposal_created_ms=NOON_MS,
        proposed_price=entry,
        live_price=entry,
    )
    assert first_blocker(checks) is None
    invalidate_live_cache()
