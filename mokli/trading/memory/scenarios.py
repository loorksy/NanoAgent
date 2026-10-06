"""Scenario outcomes grouped by market regime (R11)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ScenarioMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS scenario_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regime TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    r_multiple REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(self, *, regime: str, scenario_id: str, r_multiple: float) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO scenario_outcomes (regime, scenario_id, r_multiple) VALUES (?, ?, ?)",
                (regime, scenario_id, r_multiple),
            )

    def stats(self, regime: str) -> dict[str, object]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT r_multiple FROM scenario_outcomes WHERE regime = ?",
                (regime,),
            ).fetchall()
        values = [float(row[0]) for row in rows]
        count = len(values)
        wins = sum(1 for value in values if value > 0)
        avg = sum(values) / count if count else 0.0
        return {"regime": regime, "count": count, "wins": wins, "avg_r": avg}
