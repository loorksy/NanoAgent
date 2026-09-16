"""S7.3 — local SQLite ticket restore for gold positions after a restart."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nanobot.config.paths import get_data_dir


@dataclass(frozen=True)
class TicketRecord:
    ticket_id: str
    symbol: str
    side: str
    entry: float
    stop: float
    lot: float
    magic: int
    comment: str
    managed: bool
    adopted: bool
    opened_ms: int
    closed_ms: int
    status: str

    def to_public(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry": self.entry,
            "stop": self.stop,
            "lot": self.lot,
            "magic": self.magic,
            "comment": self.comment,
            "managed": self.managed,
            "adopted": self.adopted,
            "opened_ms": self.opened_ms,
            "closed_ms": self.closed_ms,
            "status": self.status,
        }


class TicketStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (get_data_dir() / "trading" / "tickets.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    side TEXT,
                    entry REAL,
                    stop REAL,
                    lot REAL,
                    magic INTEGER,
                    comment TEXT,
                    managed INTEGER,
                    adopted INTEGER,
                    opened_ms INTEGER,
                    closed_ms INTEGER,
                    status TEXT
                )
                """
            )

    def upsert(
        self,
        *,
        ticket_id: str,
        symbol: str = "XAUUSD",
        side: str,
        entry: float,
        stop: float,
        lot: float = 0.0,
        magic: int = 0,
        comment: str = "",
        managed: bool = True,
        adopted: bool = False,
        opened_ms: int | None = None,
        status: str = "open",
    ) -> TicketRecord:
        opened = opened_ms if opened_ms is not None else int(time.time() * 1000)
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO tickets (
                    ticket_id, symbol, side, entry, stop, lot, magic, comment,
                    managed, adopted, opened_ms, closed_ms, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    symbol=excluded.symbol,
                    side=excluded.side,
                    entry=excluded.entry,
                    stop=excluded.stop,
                    lot=excluded.lot,
                    magic=excluded.magic,
                    comment=excluded.comment,
                    managed=excluded.managed,
                    adopted=excluded.adopted,
                    status=excluded.status
                """,
                (
                    ticket_id,
                    symbol,
                    side,
                    entry,
                    stop,
                    lot,
                    magic,
                    comment,
                    int(managed),
                    int(adopted),
                    opened,
                    status,
                ),
            )
        found = self.get(ticket_id)
        assert found is not None
        return found

    def get(self, ticket_id: str) -> TicketRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT ticket_id, symbol, side, entry, stop, lot, magic, comment, "
                "managed, adopted, opened_ms, closed_ms, status FROM tickets WHERE ticket_id=?",
                (ticket_id,),
            ).fetchone()
        return None if row is None else self._row(row)

    def open_tickets(self) -> list[TicketRecord]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT ticket_id, symbol, side, entry, stop, lot, magic, comment, "
                "managed, adopted, opened_ms, closed_ms, status FROM tickets "
                "WHERE status='open'"
            ).fetchall()
        return [self._row(row) for row in rows]

    def mark_closed(self, ticket_id: str, *, closed_ms: int | None = None) -> None:
        stamp = closed_ms if closed_ms is not None else int(time.time() * 1000)
        with self._connect() as db:
            db.execute(
                "UPDATE tickets SET status='closed', closed_ms=? WHERE ticket_id=?",
                (stamp, ticket_id),
            )

    def adopt(self, ticket_id: str) -> TicketRecord | None:
        with self._connect() as db:
            db.execute(
                "UPDATE tickets SET adopted=1, managed=1, status='open' WHERE ticket_id=?",
                (ticket_id,),
            )
        return self.get(ticket_id)

    def restore(self, broker_ids: set[str]) -> list[TicketRecord]:
        """Mark persisted opens missing from the broker as closed; return still-open rows."""
        restored: list[TicketRecord] = []
        for row in self.open_tickets():
            if row.ticket_id not in broker_ids:
                self.mark_closed(row.ticket_id)
                continue
            restored.append(row)
        return restored

    def adopt_candidates(self, broker_positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        known = {row.ticket_id for row in self.open_tickets()}
        candidates: list[dict[str, Any]] = []
        for item in broker_positions:
            ticket_id = str(item.get("id") or item.get("positionId") or item.get("ticket") or "")
            if not ticket_id or ticket_id in known:
                continue
            candidates.append(
                {
                    "ticket_id": ticket_id,
                    "symbol": str(item.get("symbol") or item.get("symbolName") or ""),
                    "side": str(item.get("type") or item.get("side") or ""),
                    "entry": item.get("openPrice") or item.get("open_price") or item.get("entry"),
                    "stop": item.get("stopLoss") or item.get("stop_loss") or item.get("stop"),
                }
            )
        return candidates

    @staticmethod
    def _row(row: tuple[Any, ...]) -> TicketRecord:
        return TicketRecord(
            ticket_id=str(row[0]),
            symbol=str(row[1]),
            side=str(row[2]),
            entry=float(row[3] or 0),
            stop=float(row[4] or 0),
            lot=float(row[5] or 0),
            magic=int(row[6] or 0),
            comment=str(row[7] or ""),
            managed=bool(row[8]),
            adopted=bool(row[9]),
            opened_ms=int(row[10] or 0),
            closed_ms=int(row[11] or 0),
            status=str(row[12] or "open"),
        )
