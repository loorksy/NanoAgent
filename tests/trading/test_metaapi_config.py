"""Saved Config.trading_metaapi is the primary transport source."""

from __future__ import annotations

from nanobot.config.loader import save_config
from nanobot.config.schema import Config, TradingMetaApiConfig
from nanobot.trading.config import load_trading_config
from nanobot.trading.mt5_metaapi import NullTransport, build_transport, reset_transport


def test_saved_metaapi_reaches_transport_builder(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("METAAPI_TOKEN", raising=False)
    monkeypatch.delenv("METAAPI_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("METAAPI_REGION", raising=False)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
    config = Config(
        trading_metaapi=TradingMetaApiConfig(
            token="secret-token",
            account_id="acc-99",
            region="london",
        )
    )
    save_config(config, config_path)
    reset_transport()
    loaded = load_trading_config()
    assert loaded.metaapi_token == "secret-token"
    assert loaded.metaapi_account_id == "acc-99"
    assert loaded.metaapi_region == "london"
    public = loaded.public_metaapi()
    assert "secret-token" not in str(public)
    assert public["token_set"] is True
    assert public["account_id"] == "acc-99"
    assert public["region"] == "london"
    schema_public = config.trading_metaapi.public_view()
    assert "token" not in schema_public
    assert "secret-token" not in str(schema_public)
    transport = build_transport(loaded)
    # SDK extra is optional; credentials must be seen so NullTransport is sdk_missing, not credentials_missing.
    if isinstance(transport, NullTransport):
        assert transport.reason_key == "mt5.sdk_missing"
    else:
        assert transport.config.metaapi_token == "secret-token"
        assert transport.config.metaapi_region == "london"


def test_env_overrides_saved_metaapi(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
    save_config(
        Config(trading_metaapi=TradingMetaApiConfig(token="saved", account_id="saved-acc")),
        config_path,
    )
    monkeypatch.setenv("METAAPI_TOKEN", "env-token")
    monkeypatch.setenv("METAAPI_ACCOUNT_ID", "env-acc")
    monkeypatch.setenv("METAAPI_REGION", "singapore")
    loaded = load_trading_config()
    assert loaded.metaapi_token == "env-token"
    assert loaded.metaapi_account_id == "env-acc"
    assert loaded.metaapi_region == "singapore"
