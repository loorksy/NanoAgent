"""Single SQLite file shared by the event log, results, clients and devices."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

DB_FILENAME = "events.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    session TEXT NOT NULL,
    run TEXT,
    ts INTEGER NOT NULL,
    kind TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_session_id ON events(session, id);
CREATE INDEX IF NOT EXISTS events_kind_ts ON events(kind, ts);

CREATE TABLE IF NOT EXISTS results (
    id TEXT PRIMARY KEY,
    session TEXT,
    run TEXT,
    type TEXT NOT NULL,
    ts INTEGER NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gateway_clients (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    scopes TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    locale TEXT NOT NULL DEFAULT 'en',
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);

CREATE TABLE IF NOT EXISTS gateway_tokens (
    token_hash TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER
);
CREATE INDEX IF NOT EXISTS gateway_tokens_client ON gateway_tokens(client_id);

CREATE TABLE IF NOT EXISTS pairing_codes (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    push_token TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    locale TEXT NOT NULL DEFAULT 'en',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    revoked_at INTEGER
);

CREATE TABLE IF NOT EXISTS api_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    archived_at INTEGER
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    session TEXT,
    run TEXT,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER,
    resolved_at INTEGER,
    decision TEXT,
    source_id TEXT,
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS approvals_status ON approvals(status);
"""


class Database:
    """Thread-safe wrapper around one SQLite connection (WAL, autocommit per call)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cur.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {str(key): row[key] for key in row.keys()}


def default_db_path(workspace: Path) -> Path:
    return Path(workspace) / "agent_api" / DB_FILENAME
