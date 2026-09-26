"""Append-only per-session event log used for SSE replay (``Last-Event-ID``)."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import cast

from nanobot.agent_api.db import Database, row_to_dict
from nanobot.agent_api.events import EventKind, GatewayEvent, JsonObject

_DAY_MS = 24 * 60 * 60 * 1000


def _row_to_event(row: sqlite3.Row) -> GatewayEvent:
    record = row_to_dict(row)
    data_raw = record.get("data")
    data: JsonObject = {}
    if isinstance(data_raw, str):
        parsed: object = json.loads(data_raw)
        if isinstance(parsed, dict):
            data = cast(JsonObject, parsed)
    run = record.get("run")
    ts = record.get("ts")
    return {
        "id": str(record.get("id")),
        "session": str(record.get("session")),
        "run": run if isinstance(run, str) else None,
        "ts": ts if isinstance(ts, int) else 0,
        "kind": cast(EventKind, str(record.get("kind"))),
        "data": data,
    }


class EventLog:
    """SQLite-backed ordered log; ids are ULIDs so string order equals time order."""

    def __init__(
        self,
        db: Database,
        *,
        retention_days: int = 7,
        max_events_per_session: int = 5000,
    ) -> None:
        self._db = db
        self.retention_days = retention_days
        self.max_events_per_session = max_events_per_session

    def append(self, event: GatewayEvent) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO events(id, session, run, ts, kind, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event["id"],
                    event["session"],
                    event["run"],
                    event["ts"],
                    event["kind"],
                    json.dumps(event["data"], ensure_ascii=False, default=str),
                ),
            )

    def after(
        self, session: str, event_id: str | None, *, limit: int = 5000,
    ) -> list[GatewayEvent]:
        """Events for ``session`` with id strictly greater than ``event_id`` (all when None)."""
        with self._db.cursor() as cur:
            if event_id:
                rows = cur.execute(
                    "SELECT id, session, run, ts, kind, data FROM events "
                    "WHERE session = ? AND id > ? ORDER BY id ASC LIMIT ?",
                    (session, event_id, limit),
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT id, session, run, ts, kind, data FROM events "
                    "WHERE session = ? ORDER BY id ASC LIMIT ?",
                    (session, limit),
                ).fetchall()
        return [_row_to_event(row) for row in rows]

    def last_id(self, session: str) -> str | None:
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT id FROM events WHERE session = ? ORDER BY id DESC LIMIT 1",
                (session,),
            ).fetchone()
        if row is None:
            return None
        return str(row_to_dict(row)["id"])

    def query(
        self,
        *,
        kinds: tuple[str, ...] | None = None,
        since_ts: int | None = None,
        session: str | None = None,
        limit: int = 500,
    ) -> list[GatewayEvent]:
        clauses: list[str] = []
        params: list[object] = []
        if kinds:
            clauses.append(f"kind IN ({','.join('?' for _ in kinds)})")
            params.extend(kinds)
        if since_ts is not None:
            clauses.append("ts >= ?")
            params.append(int(since_ts))
        if session:
            clauses.append("session = ?")
            params.append(session)
        where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
        params.append(int(limit))
        with self._db.cursor() as cur:
            rows = cur.execute(
                "SELECT id, session, run, ts, kind, data FROM events "
                f"{where}ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def sessions(self) -> list[str]:
        with self._db.cursor() as cur:
            rows = cur.execute(
                "SELECT session, MAX(ts) AS last_ts FROM events GROUP BY session "
                "ORDER BY last_ts DESC"
            ).fetchall()
        return [str(row_to_dict(row)["session"]) for row in rows]

    def prune(self, *, now_ms: int | None = None) -> int:
        """Drop events older than the retention window or beyond the per-session cap."""
        now = int(time.time() * 1000) if now_ms is None else now_ms
        cutoff = now - self.retention_days * _DAY_MS
        removed = 0
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            removed += max(cur.rowcount, 0)
            rows = cur.execute(
                "SELECT session, COUNT(*) AS n FROM events GROUP BY session HAVING n > ?",
                (self.max_events_per_session,),
            ).fetchall()
            for row in rows:
                record = row_to_dict(row)
                session = str(record["session"])
                count = record["n"]
                excess = (count if isinstance(count, int) else 0) - self.max_events_per_session
                if excess <= 0:
                    continue
                cur.execute(
                    "DELETE FROM events WHERE id IN ("
                    "SELECT id FROM events WHERE session = ? ORDER BY id ASC LIMIT ?)",
                    (session, excess),
                )
                removed += max(cur.rowcount, 0)
        return removed
