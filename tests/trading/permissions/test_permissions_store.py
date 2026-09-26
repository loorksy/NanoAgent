"""PermissionStore: encrypted persistence + audit trail (08 §5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from mokli.security.secret_store import SecretStore, set_secret_store_for_tests
from mokli.trading.permissions.model import Mt5Permissions
from mokli.trading.permissions.store import (
    AUDIT_MAX_ENTRIES,
    AUDIT_SECRET_NAME,
    PERMISSIONS_SECRET_NAME,
    PermissionStore,
    get_permission_store,
    set_permission_store_for_tests,
)


@pytest.fixture
def secrets(tmp_path: Path) -> SecretStore:
    return SecretStore(tmp_path / "secrets.enc")


@pytest.fixture(autouse=True)
def _reset_globals():
    set_permission_store_for_tests(None)
    set_secret_store_for_tests(None)
    yield
    set_permission_store_for_tests(None)
    set_secret_store_for_tests(None)


def test_load_default_when_empty(secrets: SecretStore) -> None:
    store = PermissionStore(secrets)
    assert store.load() == Mt5Permissions()
    assert store.audit() == []


def test_save_persists_encrypted_and_records_audit(secrets: SecretStore, tmp_path: Path) -> None:
    store = PermissionStore(secrets)
    granted = Mt5Permissions(level="execute", can_open=True, granted_by="web-1", granted_at=100)
    store.save(granted, who="web-1", now_s=123)
    assert store.load() == granted
    raw = (tmp_path / "secrets.enc").read_bytes()
    assert b"execute" not in raw
    assert PERMISSIONS_SECRET_NAME in secrets.names()
    assert AUDIT_SECRET_NAME in secrets.names()
    entries = store.audit()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["who"] == "web-1"
    assert entry["ts"] == 123
    assert entry["from_level"] == "propose"
    assert entry["to_level"] == "execute"
    assert set(entry["changed"]) == {"level", "can_open", "granted_by", "granted_at"}
    assert entry["from"]["level"] == "propose"
    assert entry["to"]["level"] == "execute"
    assert entry["to"]["can_open"] is True


def test_unchanged_save_does_not_add_audit(secrets: SecretStore) -> None:
    store = PermissionStore(secrets)
    store.save(Mt5Permissions(), who="a", now_s=1)
    assert store.audit() == []
    store.save(Mt5Permissions(level="recommend"), who="b", now_s=2)
    store.save(Mt5Permissions(level="recommend"), who="c", now_s=3)
    assert [row["who"] for row in store.audit()] == ["b"]


def test_audit_newest_first_and_bounded(secrets: SecretStore) -> None:
    store = PermissionStore(secrets)
    for index in range(AUDIT_MAX_ENTRIES + 5):
        level = "execute" if index % 2 else "recommend"
        store.save(Mt5Permissions(level=level), who=f"u{index}", now_s=index)
    rows = store.audit(limit=AUDIT_MAX_ENTRIES + 50)
    assert len(rows) == AUDIT_MAX_ENTRIES
    assert rows[0]["who"] == f"u{AUDIT_MAX_ENTRIES + 4}"
    assert store.audit(limit=3)[2]["who"] == f"u{AUDIT_MAX_ENTRIES + 2}"
    assert store.audit(limit=0) == []


def test_reset_returns_to_default(secrets: SecretStore) -> None:
    store = PermissionStore(secrets)
    store.save(Mt5Permissions(level="execute", can_open=True), who="a", now_s=1)
    out = store.reset(who="kill", now_s=2)
    assert out == Mt5Permissions()
    assert store.load() == Mt5Permissions()
    assert store.audit()[0]["who"] == "kill"
    assert store.audit()[0]["to_level"] == "propose"


def test_corrupt_payload_falls_back_to_default(secrets: SecretStore) -> None:
    secrets.set(PERMISSIONS_SECRET_NAME, "{not json")
    assert PermissionStore(secrets).load() == Mt5Permissions()
    secrets.set(PERMISSIONS_SECRET_NAME, json.dumps({"level": "god"}))
    assert PermissionStore(secrets).load() == Mt5Permissions()
    secrets.set(PERMISSIONS_SECRET_NAME, json.dumps([1, 2]))
    assert PermissionStore(secrets).load() == Mt5Permissions()
    secrets.set(AUDIT_SECRET_NAME, "nope")
    assert PermissionStore(secrets).audit() == []


def test_unreadable_secret_store_falls_back_to_default(tmp_path: Path) -> None:
    good = SecretStore(tmp_path / "secrets.enc")
    PermissionStore(good).save(Mt5Permissions(level="execute"), who="a", now_s=1)
    wrong_key = SecretStore(tmp_path / "secrets.enc", master_key=Fernet.generate_key())
    store = PermissionStore(wrong_key)
    assert store.load() == Mt5Permissions()
    assert store.audit() == []


def test_global_store_uses_global_secret_store(secrets: SecretStore) -> None:
    set_secret_store_for_tests(secrets)
    store = get_permission_store()
    assert store is get_permission_store()
    assert store.secrets is secrets
    store.save(Mt5Permissions(level="recommend"), who="x", now_s=1)
    assert PermissionStore(secrets).load().level == "recommend"
