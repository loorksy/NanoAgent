"""Encrypted persistence for ``Mt5Permissions`` plus a change audit (08 §5).

Both records live in the Fernet secret store next to the MT5 password:
``mt5_permissions`` (current grant) and ``mt5_permissions_audit`` (who / from /
to / ts per change, newest last, bounded).
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Final, cast

from loguru import logger
from pydantic import ValidationError

from mokli.security.secret_store import SecretStore, SecretStoreError, get_secret_store
from mokli.trading.permissions.model import Mt5Permissions

PERMISSIONS_SECRET_NAME: Final[str] = "mt5_permissions"
AUDIT_SECRET_NAME: Final[str] = "mt5_permissions_audit"
AUDIT_MAX_ENTRIES: Final[int] = 200


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


class PermissionStore:
    """Load/save the grant; every save appends an audit entry when something changed."""

    def __init__(self, secrets: SecretStore | None = None) -> None:
        self._secrets = secrets
        self._lock = threading.RLock()

    @property
    def secrets(self) -> SecretStore:
        return self._secrets if self._secrets is not None else get_secret_store()

    def load(self) -> Mt5Permissions:
        """Current grant; unreadable or invalid storage falls back to the safe default."""
        with self._lock:
            try:
                raw = self.secrets.get(PERMISSIONS_SECRET_NAME)
            except (SecretStoreError, OSError) as exc:
                logger.warning("mt5 permissions unreadable, using defaults: {}", exc)
                return Mt5Permissions()
        if not raw:
            return Mt5Permissions()
        try:
            data: object = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("permissions payload is not an object")
            return Mt5Permissions.model_validate(cast(dict[str, Any], data))
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            logger.warning("mt5 permissions corrupt, using defaults: {}", exc)
            return Mt5Permissions()

    def save(
        self,
        permissions: Mt5Permissions,
        *,
        who: str,
        now_s: float | None = None,
    ) -> Mt5Permissions:
        """Persist ``permissions`` and record the diff against the stored grant."""
        ts = int(now_s if now_s is not None else time.time())
        with self._lock:
            before = self.load()
            before_dump = before.model_dump(mode="json")
            after_dump = permissions.model_dump(mode="json")
            changed = _changed_fields(before_dump, after_dump)
            self.secrets.set(PERMISSIONS_SECRET_NAME, json.dumps(after_dump, sort_keys=True))
            if changed:
                entry: dict[str, Any] = {
                    "who": who or "unknown",
                    "ts": ts,
                    "from": {key: before_dump.get(key) for key in changed},
                    "to": {key: after_dump.get(key) for key in changed},
                    "changed": changed,
                }
                if "level" in changed:
                    entry["from_level"] = before.level
                    entry["to_level"] = permissions.level
                self._append_audit(entry)
        return permissions

    def reset(self, *, who: str, now_s: float | None = None) -> Mt5Permissions:
        """Return to the default grant (level ``propose``)."""
        return self.save(Mt5Permissions(), who=who, now_s=now_s)

    def audit(self, limit: int = 50) -> list[dict[str, Any]]:
        """Most recent audit entries, newest first."""
        with self._lock:
            entries = self._read_audit()
        if limit <= 0:
            return []
        return list(reversed(entries))[:limit]

    # -- internals ----------------------------------------------------------

    def _read_audit(self) -> list[dict[str, Any]]:
        try:
            raw = self.secrets.get(AUDIT_SECRET_NAME)
        except (SecretStoreError, OSError) as exc:
            logger.warning("mt5 permissions audit unreadable: {}", exc)
            return []
        if not raw:
            return []
        try:
            data: object = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in cast(list[object], data):
            if isinstance(item, dict):
                rows.append(cast(dict[str, Any], item))
        return rows

    def _append_audit(self, entry: dict[str, Any]) -> None:
        entries = self._read_audit()
        entries.append(entry)
        if len(entries) > AUDIT_MAX_ENTRIES:
            entries = entries[-AUDIT_MAX_ENTRIES:]
        self.secrets.set(AUDIT_SECRET_NAME, json.dumps(entries, sort_keys=True))


_store: PermissionStore | None = None
_store_lock = threading.Lock()


def get_permission_store() -> PermissionStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = PermissionStore()
        return _store


def set_permission_store_for_tests(store: PermissionStore | None) -> None:
    global _store
    with _store_lock:
        _store = store
