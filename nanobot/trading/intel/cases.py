"""Similar-case index (R8). Fingerprint plus outcome, ranked by overlap."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def atr_bucket(atr: float) -> str:
    return f"{round(atr, 1):.1f}"


class CaseIndex:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setup TEXT NOT NULL,
                    side TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    atr_bucket TEXT NOT NULL,
                    outcome_r REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(
        self,
        *,
        setup: str,
        side: str,
        regime: str,
        atr: float,
        outcome_r: float,
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO cases (setup, side, regime, atr_bucket, outcome_r) VALUES (?, ?, ?, ?, ?)",
                (setup, side, regime, atr_bucket(atr), outcome_r),
            )

    def similar(
        self,
        *,
        setup: str,
        side: str,
        regime: str,
        atr: float,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        bucket = atr_bucket(atr)
        with self._connect() as db:
            rows = db.execute(
                "SELECT setup, side, regime, atr_bucket, outcome_r FROM cases"
            ).fetchall()
        ranked: list[tuple[float, dict[str, object]]] = []
        for setup_v, side_v, regime_v, bucket_v, outcome in rows:
            score = 0.0
            if setup_v == setup and side_v == side and regime_v == regime:
                score = 1.0
            elif setup_v == setup and side_v == side:
                score = 0.6
            elif regime_v == regime:
                score = 0.3
            if bucket_v == bucket:
                score += 0.1
            if score <= 0:
                continue
            ranked.append(
                (
                    score,
                    {
                        "setup": setup_v,
                        "side": side_v,
                        "regime": regime_v,
                        "atr_bucket": bucket_v,
                        "outcome_r": outcome,
                        "score": round(score, 2),
                    },
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in ranked[:limit]]
