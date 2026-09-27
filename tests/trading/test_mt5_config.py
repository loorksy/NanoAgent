"""Saved Config.trading_mt5 is the primary transport source."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from mokli.config.loader import load_config, save_config
from mokli.config.schema import Config, TradingMt5Config
from mokli.security.secret_store import SecretStore, set_secret_store_for_tests
from mokli.trading.config import load_trading_config
from mokli.trading.mt5_broker import NullTransport, build_transport, reset_transport


def _isolate(tmp_path, monkeypatch) -> SecretStore:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("mokli.config.loader._current_config_path", config_path)
    store = SecretStore(tmp_path / "secrets.enc")
    set_secret_store_for_tests(store)
    for name in ("MT5_HOST", "MT5_PORT", "MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER"):
        monkeypatch.delenv(name, raising=False)
    return store


def test_trading_mt5_extra_uses_mt5linux_client() -> None:
    extras = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    trading_mt5 = extras["trading-mt5"]
    assert any(dep.startswith("mt5linux>=0.2.4,<1") for dep in trading_mt5)
    assert not any(dep.startswith("metaapi-cloud-sdk") for dep in trading_mt5)
    dev = extras["dev"]
    assert not any(dep.startswith("metaapi-cloud-sdk") for dep in dev)


def test_saved_mt5_reaches_transport_builder(tmp_path, monkeypatch) -> None:
    store = _isolate(tmp_path, monkeypatch)
    store.set("mt5_password", "secret-pass")
    config = Config(
        trading_mt5=TradingMt5Config(
            login="10001",
            server="Broker-Demo",
            host="mt5.internal",
            port=8002,
        )
    )
    save_config(config, tmp_path / "config.json")
    reset_transport()
    loaded = load_trading_config()
    assert loaded.mt5_login == "10001"
    assert loaded.mt5_server == "Broker-Demo"
    assert loaded.mt5_host == "mt5.internal"
    assert loaded.mt5_port == 8002
    assert loaded.mt5_password == "secret-pass"
    public = loaded.public_mt5()
    assert "secret-pass" not in str(public)
    assert "secret-pass" not in repr(loaded)
    assert public["password_set"] is True
    assert public["login"] == "10001"
    schema_public = config.trading_mt5.public_view()
    assert "password" not in schema_public
    assert "secret-pass" not in str(schema_public)
    transport = build_transport(loaded)
    if isinstance(transport, NullTransport):
        assert transport.reason_key == "mt5.sdk_missing"
    else:
        assert transport.config.mt5_login == "10001"
        assert transport.config.mt5_server == "Broker-Demo"


def test_env_overrides_saved_mt5(tmp_path, monkeypatch) -> None:
    store = _isolate(tmp_path, monkeypatch)
    store.set("mt5_password", "saved-pass")
    save_config(
        Config(trading_mt5=TradingMt5Config(login="10001", server="Saved", host="saved.internal")),
        tmp_path / "config.json",
    )
    monkeypatch.setenv("MT5_HOST", "10.1.1.8")
    monkeypatch.setenv("MT5_PORT", "9001")
    monkeypatch.setenv("MT5_LOGIN", "42")
    monkeypatch.setenv("MT5_PASSWORD", "env-pass")
    monkeypatch.setenv("MT5_SERVER", "Env-Server")
    loaded = load_trading_config()
    assert loaded.mt5_host == "10.1.1.8"
    assert loaded.mt5_port == 9001
    assert loaded.mt5_login == "42"
    assert loaded.mt5_password == "env-pass"
    assert loaded.mt5_server == "Env-Server"
    assert "env-pass" not in str(loaded.public_mt5())


def test_host_and_port_default_when_unset(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    loaded = load_trading_config()
    assert loaded.mt5_host == "localhost"
    assert loaded.mt5_port == 8001
    assert loaded.mt5_configured is False


def test_legacy_metaapi_config_object_still_loads(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"trading_metaapi": {"token": "old-token", "account_id": "acc", "region": "london"}}),
        encoding="utf-8",
    )
    loaded = load_config(path)
    assert loaded.trading_mt5.login == ""
    assert loaded.trading_mt5.host == "localhost"
    assert loaded.trading_mt5.port == 8001
    assert "old-token" not in str(loaded.trading_mt5.public_view())
