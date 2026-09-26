"""Similar-case index (R8). Fingerprint, note, and close path, ranked together."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

from mokli.trading.intel.dtw_matcher import match_pattern
from mokli.trading.intel.vector_playbook import VectorPlaybook


def atr_bucket(atr: float) -> str:
    return f"{round(atr, 1):.1f}"


def _closes(raw: object) -> list[float]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    values: list[float] = []
    for item in cast(list[object], parsed):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        values.append(float(item))
    return values


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
                    outcome_r REAL NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    closes TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(cases)")}
            if "note" not in columns:
                db.execute("ALTER TABLE cases ADD COLUMN note TEXT NOT NULL DEFAULT ''")
            if "closes" not in columns:
                db.execute("ALTER TABLE cases ADD COLUMN closes TEXT NOT NULL DEFAULT '[]'")

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
        note: str = "",
        closes: list[float] | None = None,
    ) -> None:
        payload = json.dumps(list(closes or []))
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO cases
                    (setup, side, regime, atr_bucket, outcome_r, note, closes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (setup, side, regime, atr_bucket(atr), outcome_r, note, payload),
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
                "SELECT setup, side, regime, atr_bucket, outcome_r, note, closes FROM cases"
            ).fetchall()
        ranked: list[tuple[float, dict[str, object]]] = []
        for setup_v, side_v, regime_v, bucket_v, outcome, note, closes_raw in rows:
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
                        "note": str(note or ""),
                        "closes": _closes(closes_raw),
                        "score": round(score, 2),
                    },
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in ranked[:limit]]

    def similar_market(
        self,
        *,
        setup: str,
        side: str,
        regime: str,
        atr: float,
        note: str = "",
        closes: list[float] | None = None,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """Blend the fingerprint with playbook cosine and a DTW close-path match."""
        base = self.similar(setup=setup, side=side, regime=regime, atr=atr, limit=limit)
        if not base:
            return []
        query = note or f"{setup} {side} {regime}"
        notes = [str(row.get("note") or "") for row in base]
        book = VectorPlaybook(scenarios=notes or [query])
        playbook = {match.scenario: match.score for match in book.query(query, k=len(book.scenarios))}
        series = list(closes or [])
        blended: list[dict[str, object]] = []
        for row in base:
            path = _closes(json.dumps(row.get("closes"))) if isinstance(row.get("closes"), list) else []
            pattern = 0.0
            if series and path:
                pattern = match_pattern(series, templates={"case": path}).confidence
            note_score = float(playbook.get(str(row.get("note") or ""), 0.0))
            fingerprint = float(cast(float, row["score"]))
            item = dict(row)
            item["playbook"] = round(note_score, 4)
            item["pattern"] = round(pattern, 4)
            item["blended"] = round((fingerprint + note_score + pattern) / 3.0, 4)
            blended.append(item)
        blended.sort(key=lambda item: float(cast(float, item["blended"])), reverse=True)
        return blended[:limit]
