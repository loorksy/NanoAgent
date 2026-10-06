"""Push device registry (FCM / APNs tokens) bound to gateway clients."""

from __future__ import annotations

import secrets
import sqlite3
from typing import Literal, TypedDict

from mokli.agent_api.db import Database, row_to_dict
from mokli.agent_api.events import now_ms

Platform = Literal["android", "ios", "web"]


class DeviceRecord(TypedDict):
    id: str
    client_id: str
    platform: Platform
    push_token: str
    label: str
    locale: str
    created_at: int
    updated_at: int
    revoked: bool


def _platform(value: object) -> Platform:
    if value in ("android", "ios", "web"):
        return value
    return "web"


def _row(row: sqlite3.Row) -> DeviceRecord:
    record = row_to_dict(row)
    created = record.get("created_at")
    updated = record.get("updated_at")
    return {
        "id": str(record["id"]),
        "client_id": str(record.get("client_id") or ""),
        "platform": _platform(record.get("platform")),
        "push_token": str(record.get("push_token") or ""),
        "label": str(record.get("label") or ""),
        "locale": str(record.get("locale") or "en"),
        "created_at": created if isinstance(created, int) else 0,
        "updated_at": updated if isinstance(updated, int) else 0,
        "revoked": record.get("revoked_at") is not None,
    }


def public_device(device: DeviceRecord) -> dict[str, object]:
    """Device view without the raw push token."""
    return {
        "id": device["id"],
        "client_id": device["client_id"],
        "platform": device["platform"],
        "label": device["label"],
        "locale": device["locale"],
        "created_at": device["created_at"],
        "updated_at": device["updated_at"],
        "revoked": device["revoked"],
    }


class DeviceRegistry:
    def __init__(self, db: Database) -> None:
        self._db = db

    def register(
        self,
        *,
        client_id: str,
        platform: Platform,
        push_token: str,
        label: str = "",
        locale: str = "en",
    ) -> DeviceRecord:
        now = now_ms()
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT id FROM devices WHERE client_id = ? AND push_token = ?",
                (client_id, push_token),
            ).fetchone()
            if row is not None:
                device_id = str(row_to_dict(row)["id"])
                cur.execute(
                    "UPDATE devices SET platform = ?, label = ?, locale = ?, updated_at = ?, "
                    "revoked_at = NULL WHERE id = ?",
                    (platform, label, locale, now, device_id),
                )
            else:
                device_id = f"d_{secrets.token_hex(8)}"
                cur.execute(
                    "INSERT INTO devices(id, client_id, platform, push_token, label, locale, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (device_id, client_id, platform, push_token, label, locale, now, now),
                )
        device = self.get(device_id)
        assert device is not None
        return device

    def get(self, device_id: str) -> DeviceRecord | None:
        with self._db.cursor() as cur:
            row = cur.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        return _row(row) if row is not None else None

    def list(self, *, client_id: str | None = None, include_revoked: bool = False) -> list[DeviceRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if client_id is not None:
            clauses.append("client_id = ?")
            params.append(client_id)
        if not include_revoked:
            clauses.append("revoked_at IS NULL")
        where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
        with self._db.cursor() as cur:
            rows = cur.execute(
                f"SELECT * FROM devices {where}ORDER BY updated_at DESC", params,
            ).fetchall()
        return [_row(row) for row in rows]

    def revoke(self, device_id: str) -> bool:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE devices SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (now_ms(), device_id),
            )
            return cur.rowcount > 0

    def revoke_for_client(self, client_id: str) -> int:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE devices SET revoked_at = ? WHERE client_id = ? AND revoked_at IS NULL",
                (now_ms(), client_id),
            )
            return max(cur.rowcount, 0)
