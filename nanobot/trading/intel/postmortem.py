"""FEATURE-08 — SQLite post-mortem log of losing trades."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from nanobot.config.paths import get_data_dir


@dataclass(frozen=True)
class LossRecord:
    entry: float
    stop: float
    closed_at_ms: int
    dxy_state: str
    setup: str
    spread_points: float
    reason: str
    side: str = "buy"


class PostMortemLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (get_data_dir() / "trading" / "postmortem.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS losses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry REAL,
                    stop REAL,
                    closed_at_ms INTEGER,
                    dxy_state TEXT,
                    setup TEXT,
                    spread_points REAL,
                    reason TEXT,
                    side TEXT
                )
                """
            )

    def record(self, rec: LossRecord) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO losses (entry, stop, closed_at_ms, dxy_state, setup, spread_points, reason, side)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.entry,
                    rec.stop,
                    rec.closed_at_ms,
                    rec.dxy_state,
                    rec.setup,
                    rec.spread_points,
                    rec.reason,
                    rec.side,
                ),
            )

    def recent_losses(self, n: int = 3) -> list[LossRecord]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT entry, stop, closed_at_ms, dxy_state, setup, spread_points, reason, side "
                "FROM losses ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [
            LossRecord(
                entry=r[0],
                stop=r[1],
                closed_at_ms=r[2],
                dxy_state=r[3],
                setup=r[4],
                spread_points=r[5],
                reason=r[6],
                side=r[7],
            )
            for r in rows
        ]

    def repeats_recent_error(
        self,
        *,
        setup: str,
        dxy_state: str,
        side: str,
        n: int = 3,
    ) -> LossRecord | None:
        for rec in self.recent_losses(n):
            if rec.setup == setup and rec.dxy_state == dxy_state and rec.side == side:
                return rec
        return None


def refuse_repeat_error(
    *,
    side: str,
    setup: str,
    dxy_state: str = "unknown",
    n: int = 3,
    path: Path | None = None,
) -> LossRecord | None:
    """FEATURE-08 / S5.4 — refuse a new idea that clones recent losing conditions."""
    return PostMortemLog(path).repeats_recent_error(
        setup=setup,
        dxy_state=dxy_state,
        side=side,
        n=n,
    )


def record_stop_hit(
    *,
    entry: float,
    stop: float,
    dxy_state: str,
    setup: str,
    spread_points: float,
    reason: str,
    side: str = "buy",
    path: Path | None = None,
) -> None:
    PostMortemLog(path).record(
        LossRecord(
            entry=entry,
            stop=stop,
            closed_at_ms=int(time.time() * 1000),
            dxy_state=dxy_state,
            setup=setup,
            spread_points=spread_points,
            reason=reason,
            side=side,
        )
    )
