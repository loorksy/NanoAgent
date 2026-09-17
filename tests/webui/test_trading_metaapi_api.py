from __future__ import annotations

import json

import pytest

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import Config
from nanobot.trading.mt5_metaapi import NullTransport, reset_transport
from nanobot.webui.trading_metaapi_api import (
    TradingMetaApiError,
    trading_metaapi_action,
    trading_metaapi_payload,
    trading_metaapi_settings_action,
)


def _use_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    save_config(Config(), config_path)
    monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
    monkeypatch.delenv("METAAPI_TOKEN", raising=False)
    monkeypatch.delenv("METAAPI_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("METAAPI_REGION", raising=False)
    reset_transport()


def test_trading_metaapi_payload_hides_secrets(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    from nanobot.config.schema import TradingMetaApiConfig

    config = load_config()
    config.trading_metaapi = TradingMetaApiConfig(
        token="super-secret-token",
        account_id="acc-1",
        region="london",
    )
    save_config(config)
    reset_transport()
    payload = trading_metaapi_payload()
    blob = json.dumps(payload)
    assert "super-secret-token" not in blob
    assert "password" not in payload
    assert payload["token_set"] is True
    assert payload["configured"] is True
    assert payload["account_id"] == "acc-1"
    assert payload["region"] == "london"
    assert payload["title"] == "Connect MT5 account"
    assert "token" not in payload


@pytest.mark.asyncio
async def test_trading_metaapi_update_saves_account_id(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    payload = await trading_metaapi_action(
        "update",
        {
            "token": ["secret-token"],
            "account_id": ["acc-42"],
            "region": ["singapore"],
        },
    )
    assert payload["account_id"] == "acc-42"
    assert payload["region"] == "singapore"
    assert payload["configured"] is True
    assert "secret-token" not in json.dumps(payload)
    saved = load_config()
    assert saved.trading_metaapi.token == "secret-token"
    assert saved.trading_metaapi.account_id == "acc-42"
    assert payload["last_action"]["ok"] is True


@pytest.mark.asyncio
async def test_trading_metaapi_provision_does_not_store_password(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_provision(**kwargs):
        assert kwargs["login"] == "77001"
        assert kwargs["password"] == "broker-pass"
        assert kwargs["server"] == "Broker-Demo"
        return {"ok": True, "account_id": "prov-9"}

    monkeypatch.setattr(
        "nanobot.webui.trading_metaapi_api.provision_mt5_account",
        fake_provision,
    )
    payload = await trading_metaapi_action(
        "update",
        {
            "token": ["secret-token"],
            "login": ["77001"],
            "password": ["broker-pass"],
            "server": ["Broker-Demo"],
            "region": ["new-york"],
        },
    )
    assert payload["account_id"] == "prov-9"
    blob = json.dumps(payload)
    assert "broker-pass" not in blob
    saved = load_config()
    dumped = saved.model_dump()
    assert "broker-pass" not in json.dumps(dumped)
    assert saved.trading_metaapi.account_id == "prov-9"


@pytest.mark.asyncio
async def test_trading_metaapi_arabic_labels(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    payload = trading_metaapi_payload(locale="ar")
    assert payload["title"] == "ربط حساب MT5"
    assert payload["connect_label"] == "ربط MT5"


@pytest.mark.asyncio
async def test_trading_metaapi_disconnect(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    await trading_metaapi_action(
        "update",
        {"token": ["secret-token"], "account_id": ["acc-42"]},
    )
    payload = await trading_metaapi_action("disconnect", {})
    assert payload["configured"] is False
    assert payload["account_id"] == ""
    saved = load_config()
    assert saved.trading_metaapi.token == ""
    assert saved.trading_metaapi.account_id == ""


@pytest.mark.asyncio
async def test_trading_metaapi_env_blocks_disconnect(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    monkeypatch.setenv("METAAPI_TOKEN", "env-token")
    monkeypatch.setenv("METAAPI_ACCOUNT_ID", "env-acc")
    with pytest.raises(TradingMetaApiError, match="environment"):
        await trading_metaapi_action("disconnect", {})


@pytest.mark.asyncio
async def test_trading_metaapi_rejects_incomplete_login(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    with pytest.raises(TradingMetaApiError, match="login"):
        await trading_metaapi_action(
            "update",
            {"token": ["secret-token"], "login": ["77001"]},
        )


@pytest.mark.asyncio
async def test_trading_metaapi_test_uses_transport(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    class OkTransport(NullTransport):
        async def account_snapshot(self):
            return {
                "ok": True,
                "account": {
                    "login": "77001",
                    "balance": 1000,
                    "currency": "USD",
                    "password": "should-not-leak",
                },
            }

    monkeypatch.setattr(
        "nanobot.webui.trading_metaapi_api.get_transport",
        lambda: OkTransport("mt5.sdk_missing"),
    )
    payload = await trading_metaapi_action("test", {})
    assert payload["account"]["login"] == "77001"
    assert payload["account"]["balance"] == 1000
    assert "should-not-leak" not in json.dumps(payload)
    assert payload["last_action"]["ok"] is True


@pytest.mark.asyncio
async def test_trading_metaapi_settings_list(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    listed = await trading_metaapi_settings_action(None, {"locale": ["ar"]})
    assert listed["title"] == "ربط حساب MT5"
