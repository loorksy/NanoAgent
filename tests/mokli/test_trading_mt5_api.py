from __future__ import annotations

import json

import pytest

from mokli.config.loader import load_config, save_config
from mokli.config.schema import Config, TradingMt5Config
from mokli.security.secret_store import SecretStore, get_secret_store, set_secret_store_for_tests
from mokli.surface.trading_mt5_api import (
    TradingMt5Error,
    trading_mt5_action,
    trading_mt5_payload,
    trading_mt5_settings_action,
)
from mokli.trading.mt5_broker import reset_transport


def _use_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    save_config(Config(), config_path)
    monkeypatch.setattr("mokli.config.loader._current_config_path", config_path)
    set_secret_store_for_tests(SecretStore(tmp_path / "secrets.enc"))
    for name in ("MT5_HOST", "MT5_PORT", "MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER"):
        monkeypatch.delenv(name, raising=False)
    reset_transport()


def test_trading_mt5_payload_hides_password(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    get_secret_store().set("mt5_password", "super-secret")
    config = load_config()
    config.trading_mt5 = TradingMt5Config(login="10001", server="Broker-Demo", host="mt5.internal", port=8002)
    save_config(config)
    reset_transport()
    payload = trading_mt5_payload()
    blob = json.dumps(payload)
    assert "super-secret" not in blob
    assert "password" not in payload
    assert payload["password_set"] is True
    assert payload["configured"] is True
    assert payload["login"] == "10001"
    assert payload["server"] == "Broker-Demo"
    assert payload["host"] == "mt5.internal"
    assert payload["port"] == 8002
    assert payload["title"] == "Connect MT5 account"


@pytest.mark.asyncio
async def test_trading_mt5_update_validates_then_stores_password(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    seen: dict[str, str] = {}

    async def fake_validate(draft):
        seen["password"] = draft.password
        return {"login": draft.login, "name": "Desk", "balance": 10, "currency": "USD", "server": draft.server}

    monkeypatch.setattr("mokli.surface.trading_mt5_api._validate_live", fake_validate)
    payload = await trading_mt5_action(
        "update",
        {
            "login": ["10001"],
            "password": ["broker-pass"],
            "server": ["Broker-Demo"],
            "host": ["mt5.internal"],
            "port": ["8002"],
        },
    )
    assert seen["password"] == "broker-pass"
    assert payload["login"] == "10001"
    assert payload["connected"] is True
    assert payload["account"]["name"] == "Desk"
    blob = json.dumps(payload)
    assert "broker-pass" not in blob
    saved = load_config()
    assert saved.trading_mt5.login == "10001"
    assert saved.trading_mt5.server == "Broker-Demo"
    assert saved.trading_mt5.host == "mt5.internal"
    assert saved.trading_mt5.port == 8002
    assert "broker-pass" not in json.dumps(saved.model_dump())
    assert get_secret_store().get("mt5_password") == "broker-pass"
    assert payload["last_action"]["ok"] is True


@pytest.mark.asyncio
async def test_trading_mt5_failed_login_does_not_store_password(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_validate(draft):
        raise TradingMt5Error("MT5 connection test failed: rejected")

    monkeypatch.setattr("mokli.surface.trading_mt5_api._validate_live", fake_validate)
    with pytest.raises(TradingMt5Error, match="rejected"):
        await trading_mt5_action(
            "update",
            {"login": ["10001"], "password": ["broker-pass"], "server": ["Broker-Demo"]},
        )
    assert get_secret_store().get("mt5_password") is None
    assert load_config().trading_mt5.login == ""


@pytest.mark.asyncio
async def test_session_adopts_window_account_without_password(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_read(**kwargs):
        assert kwargs["ipc_timeout_ms"] == 8000
        return {"login": "256952586", "server": "Exness-MT5Real35", "name": "Desk", "currency": "USD"}

    monkeypatch.setattr("mokli.surface.trading_mt5_api.read_terminal_account", fake_read)
    payload = await trading_mt5_action("session", {})
    assert payload["connected"] is True
    assert payload["login"] == "256952586"
    assert payload["server"] == "Exness-MT5Real35"
    assert payload["password_set"] is False
    saved = load_config().trading_mt5
    assert saved.terminal_session is True
    assert get_secret_store().get("mt5_password") is None
    assert "256952586" in json.dumps(payload)
    assert payload["password_set"] is False


@pytest.mark.asyncio
async def test_session_without_account_does_not_store(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_read(**kwargs):
        del kwargs
        return None

    monkeypatch.setattr("mokli.surface.trading_mt5_api.read_terminal_account", fake_read)
    payload = await trading_mt5_action("session", {})
    assert payload["connected"] is False
    assert load_config().trading_mt5.login == ""


@pytest.mark.asyncio
async def test_trading_mt5_arabic_labels(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    payload = trading_mt5_payload(locale="ar")
    assert payload["title"] == "ربط حساب MT5"
    assert payload["connect_label"] == "ربط MT5"


@pytest.mark.asyncio
async def test_trading_mt5_disconnect(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_validate(draft):
        return {"login": draft.login, "name": "Desk"}

    monkeypatch.setattr("mokli.surface.trading_mt5_api._validate_live", fake_validate)
    await trading_mt5_action(
        "update",
        {"login": ["10001"], "password": ["broker-pass"], "server": ["Broker-Demo"]},
    )
    payload = await trading_mt5_action("disconnect", {})
    assert payload["configured"] is False
    assert payload["login"] == ""
    assert get_secret_store().get("mt5_password") is None
    assert "broker-pass" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_trading_mt5_env_blocks_disconnect(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    monkeypatch.setenv("MT5_LOGIN", "42")
    monkeypatch.setenv("MT5_PASSWORD", "env-pass")
    monkeypatch.setenv("MT5_SERVER", "Env")
    with pytest.raises(TradingMt5Error, match="environment"):
        await trading_mt5_action("disconnect", {})


@pytest.mark.asyncio
async def test_trading_mt5_update_uses_env_bridge_when_form_omits_host(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    monkeypatch.setenv("MT5_HOST", "10.0.0.8")
    monkeypatch.setenv("MT5_PORT", "8001")

    async def fake_validate(draft):
        assert draft.host == "10.0.0.8"
        assert draft.port == 8001
        return {"login": draft.login, "name": "Desk", "server": draft.server}

    monkeypatch.setattr("mokli.surface.trading_mt5_api._validate_live", fake_validate)
    await trading_mt5_action(
        "update",
        {"login": ["10001"], "password": ["broker-pass"], "server": ["Broker-Demo"]},
    )
    saved = load_config()
    assert saved.trading_mt5.host == "10.0.0.8"
    assert saved.trading_mt5.port == 8001


@pytest.mark.asyncio
async def test_trading_mt5_rejects_incomplete_login(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)
    with pytest.raises(TradingMt5Error, match="login"):
        await trading_mt5_action("update", {"login": ["10001"]})


@pytest.mark.asyncio
async def test_trading_mt5_status_uses_one_attempt(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_probe(locale, *, attempts):
        assert attempts == 1
        return ({"login": "10001", "name": "Desk"}, None, True)

    monkeypatch.setattr("mokli.surface.trading_mt5_api._probe", fake_probe)
    payload = await trading_mt5_action("status", {})
    assert payload["connected"] is True
    assert payload["account"]["name"] == "Desk"
    assert payload["account"]["login"] == "10001"


@pytest.mark.asyncio
async def test_trading_mt5_test_uses_probe(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)

    async def fake_probe(locale, *, attempts):
        return (
            {
                "login": "10001",
                "balance": 1000,
                "currency": "USD",
                "name": "Desk",
                "password": "should-not-leak",
            },
            None,
            True,
        )

    monkeypatch.setattr("mokli.surface.trading_mt5_api._probe", fake_probe)
    payload = await trading_mt5_action("test", {})
    assert payload["account"]["login"] == "10001"
    assert payload["account"]["balance"] == 1000
    assert payload["connected"] is True
    assert "should-not-leak" not in json.dumps(payload)
    assert payload["last_action"]["ok"] is True


@pytest.mark.asyncio
async def test_trading_mt5_settings_list(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(tmp_path, monkeypatch)
    listed = await trading_mt5_settings_action(None, {"locale": ["ar"]})
    assert listed["title"] == "ربط حساب MT5"
