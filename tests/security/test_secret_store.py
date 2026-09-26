"""Fernet secret store: encryption at rest, key handling, atomic writes, config fallback."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from mokli.config.schema import TradingMetaApiConfig, TradingOandaConfig
from mokli.security.secret_store import (
    SECRET_KEY_ENV,
    SecretStore,
    SecretStoreError,
    get_secret_store,
    resolve_secret,
    set_secret_store_for_tests,
)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(SECRET_KEY_ENV, raising=False)
    set_secret_store_for_tests(None)
    yield
    set_secret_store_for_tests(None)


def _store(tmp_path: Path) -> SecretStore:
    return SecretStore(tmp_path / "secrets.enc")


def test_roundtrip_and_names(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.get("metaapi_token") is None
    assert store.names() == []
    store.set("metaapi_token", "tok-1")
    store.set("oanda_api_token", "tok-2")
    assert store.get("metaapi_token") == "tok-1"
    assert store.names() == ["metaapi_token", "oanda_api_token"]
    assert store.delete("metaapi_token") is True
    assert store.delete("metaapi_token") is False
    assert store.get("metaapi_token") is None
    assert store.names() == ["oanda_api_token"]


def test_file_is_encrypted_and_key_generated(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set("metaapi_token", "super-secret-value")
    raw = (tmp_path / "secrets.enc").read_bytes()
    assert b"super-secret-value" not in raw
    assert b"metaapi_token" not in raw
    key_path = tmp_path / "secret.key"
    assert key_path.exists()
    Fernet(key_path.read_bytes().strip())
    if sys.platform != "win32":
        for path in (key_path, tmp_path / "secrets.enc"):
            mode = stat.S_IMODE(os.stat(path).st_mode)
            assert mode == stat.S_IRUSR | stat.S_IWUSR, oct(mode)
    assert not list(tmp_path.glob("*.tmp"))


def test_second_instance_reads_with_same_key_file(tmp_path: Path) -> None:
    _store(tmp_path).set("a", "1")
    assert _store(tmp_path).get("a") == "1"


def test_env_master_key_overrides_key_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv(SECRET_KEY_ENV, key)
    store = _store(tmp_path)
    store.set("a", "1")
    assert not (tmp_path / "secret.key").exists()
    token = (tmp_path / "secrets.enc").read_bytes().strip()
    assert json.loads(Fernet(key.encode()).decrypt(token)) == {"a": "1"}


def test_env_passphrase_is_derived_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(SECRET_KEY_ENV, "not a fernet key but a passphrase")
    _store(tmp_path).set("a", "1")
    assert _store(tmp_path).get("a") == "1"
    monkeypatch.setenv(SECRET_KEY_ENV, "different passphrase")
    with pytest.raises(SecretStoreError):
        _store(tmp_path).get("a")


def test_wrong_key_raises_secret_store_error(tmp_path: Path) -> None:
    _store(tmp_path).set("a", "1")
    other = SecretStore(tmp_path / "secrets.enc", master_key=Fernet.generate_key())
    with pytest.raises(SecretStoreError):
        other.get("a")


def test_corrupt_payload_is_reported(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set("a", "1")
    (tmp_path / "secrets.enc").write_bytes(b"garbage")
    with pytest.raises(SecretStoreError):
        store.names()


def test_empty_name_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _store(tmp_path).set("", "x")


def test_resolve_secret_prefers_config_value(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set("metaapi_token", "stored")
    assert resolve_secret("  from-config ", "metaapi_token", store=store) == "from-config"
    assert resolve_secret("", "metaapi_token", store=store) == "stored"
    assert resolve_secret(None, "missing", store=store) == ""


def test_resolve_secret_swallows_store_errors(tmp_path: Path) -> None:
    _store(tmp_path).set("a", "1")
    broken = SecretStore(tmp_path / "secrets.enc", master_key=Fernet.generate_key())
    assert resolve_secret("", "a", store=broken) == ""


def test_default_store_uses_config_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mokli.config.loader._current_config_path", tmp_path / "config.json")
    store = get_secret_store()
    assert store.path == tmp_path / "secrets.enc"
    assert store.key_path == tmp_path / "secret.key"
    assert get_secret_store() is store


def test_config_effective_token_falls_back_to_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    set_secret_store_for_tests(store)
    store.set("metaapi_token", "meta-stored")
    store.set("oanda_api_token", "oanda-stored")

    metaapi = TradingMetaApiConfig(account_id="acc")
    assert metaapi.effective_token() == "meta-stored"
    assert metaapi.public_view()["token_set"] is False
    assert "meta-stored" not in str(metaapi.public_view())
    assert TradingMetaApiConfig(token="explicit").effective_token() == "explicit"

    oanda = TradingOandaConfig()
    assert oanda.effective_token() == "oanda-stored"
    assert oanda.public_view() == {
        "account_id": "",
        "env": "practice",
        "token_set": False,
        "configured": False,
    }
    assert TradingOandaConfig(api_token="live-token").effective_token() == "live-token"
    assert "live-token" not in repr(TradingOandaConfig(api_token="live-token"))
