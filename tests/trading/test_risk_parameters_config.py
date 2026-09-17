"""Config-driven risk thresholds must change gate behavior without code edits."""

from __future__ import annotations

import pytest

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import Config, TradingRiskParameters
from nanobot.trading.gates.rr_filter import evaluate_rr_filter
from nanobot.trading.policy import MIN_RR, invalidate_live_cache, live
from nanobot.trading.types import EntryPlan
from nanobot.webui.trading_risk_api import trading_risk_action, trading_risk_payload


def _plan(rr: float) -> EntryPlan:
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


def test_rr_filter_uses_saved_config_not_module_constant(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)

    plan = _plan(2.0)
    assert evaluate_rr_filter(plan).status == "pass"
    assert live().MIN_RR == MIN_RR

    config = Config()
    config.trading_risk_parameters.min_rr = 5.0
    save_config(config, config_path)
    invalidate_live_cache()

    assert live().MIN_RR == 5.0
    assert evaluate_rr_filter(plan).status == "veto"


def test_trading_risk_api_update_is_reflected_by_the_gate(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
    save_config(Config(), config_path)

    listed = trading_risk_payload()
    assert listed["values"]["min_rr"] == 2.0
    assert "operator's responsibility" in listed["operator_warning"]

    updated = trading_risk_action("update", {"min_rr": ["0.1"]})
    assert updated["last_action"]["ok"] is True
    assert updated["values"]["min_rr"] == 0.1
    assert load_config().trading_risk_parameters.min_rr == 0.1
    assert evaluate_rr_filter(_plan(0.5)).status == "pass"


def test_spread_guard_uses_saved_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
    from nanobot.trading.gates.risk_snapshot import RiskSnapshot
    from nanobot.trading.gates.spread_guard import evaluate_spread_guard

    save_config(Config(), config_path)
    invalidate_live_cache()
    risk = RiskSnapshot(spread_points=80)
    assert evaluate_spread_guard(risk).status == "veto"
    trading_risk_action("update", {"spread_max_points": ["200"]})
    assert evaluate_spread_guard(risk).status == "pass"


def test_schema_allows_aggressive_risk_percent() -> None:
    params = TradingRiskParameters(risk_pct_default=50.0, max_open_gold_positions=0)
    assert params.risk_pct_default == 50.0
    assert params.max_open_gold_positions == 0
