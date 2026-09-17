from __future__ import annotations

import json

import pytest

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import Config
from nanobot.trading.risk_state import DEFAULT_TOGGLES, RiskStateStore
from nanobot.webui.trading_risk_api import (
    TradingRiskError,
    trading_risk_action,
    trading_risk_payload,
    trading_risk_settings_action,
)


def _use_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    save_config(Config(), config_path)
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)


def test_trading_risk_payload_lists_defaults(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "nanobot.webui.trading_risk_api.get_risk_store",
        lambda: RiskStateStore(tmp_path / "risk.json"),
    )
    payload = trading_risk_payload()
    names = {field["name"] for group in payload["groups"] for field in group["fields"]}
    assert "risk_pct_default" in names
    assert "daily_drawdown_pct" in names
    assert "spread_max_points" in names
    assert "proposal_ttl_seconds" in names
    assert payload["values"]["risk_pct_default"] == 1.0
    assert payload["values"]["daily_drawdown_pct"] == 3.0
    assert payload["values"]["min_rr"] == 2.0
    assert payload["title"] == "Risk Parameters"
    toggle_names = {row["name"] for row in payload["toggles"]}
    assert toggle_names == set(DEFAULT_TOGGLES)
    assert all(row["never_skips_confirm"] for row in payload["toggles"])
    assert "hitl" in payload["locked_toggles"]
    assert "stale_quote" in payload["locked_toggles"]
    assert "broker_success" in payload["locked_toggles"]
    assert "hitl" not in toggle_names
    assert "stale_quote" not in toggle_names


def test_trading_risk_action_persists_json_values(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    payload = trading_risk_action(
        "update",
        {"values": [json.dumps({"risk_pct_default": 50.0, "max_open_gold_positions": 0})]},
    )
    assert payload["values"]["risk_pct_default"] == 50.0
    assert payload["values"]["max_open_gold_positions"] == 0
    saved = load_config()
    assert saved.trading_risk_parameters.risk_pct_default == 50.0
    assert saved.trading_risk_parameters.max_open_gold_positions == 0


def test_trading_risk_action_updates_toggles(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    store = RiskStateStore(tmp_path / "risk.json")
    monkeypatch.setattr("nanobot.webui.trading_risk_api.get_risk_store", lambda: store)
    payload = trading_risk_action(
        "update",
        {"toggles": [json.dumps({"news_shield": False, "rr_filter": True})]},
    )
    assert store.snapshot().feature_toggles["news_shield"] is False
    enabled = {row["name"]: row["enabled"] for row in payload["toggles"]}
    assert enabled["news_shield"] is False
    assert enabled["rr_filter"] is True


def test_trading_risk_action_rejects_locked_integrity_toggle(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    with pytest.raises(TradingRiskError, match="cannot be disabled"):
        trading_risk_action("update", {"toggles": [json.dumps({"hitl": False})]})
    with pytest.raises(TradingRiskError, match="cannot be disabled"):
        trading_risk_action("update", {"toggles": [json.dumps({"stale_quote": False})]})


def test_trading_risk_action_rejects_non_numeric(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    with pytest.raises(TradingRiskError, match="must be a number"):
        trading_risk_action("update", {"min_rr": ["abc"]})


@pytest.mark.asyncio
async def test_trading_risk_settings_action_update(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    listed = await trading_risk_settings_action(None, {})
    assert listed["values"]["pending_ttl_hours"] == 3.0
    updated = await trading_risk_settings_action("update", {"pending_ttl_hours": ["8"]})
    assert updated["values"]["pending_ttl_hours"] == 8.0
