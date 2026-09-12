"""SQLite recommendation storage."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from nanobot.config.paths import get_data_dir
from nanobot.trading.recommendations.tradability import assess_plan_tradability
from nanobot.trading.types import AgentMarketContext, ChartDrawing, FinalDecisionResult

def _db_path() -> Path:
    return get_data_dir() / "trading" / "recommendations.db"


def _conn() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendations (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL,
            stop_loss REAL,
            targets_json TEXT,
            status TEXT NOT NULL,
            summary TEXT,
            confidence REAL,
            drawings_json TEXT,
            gate_json TEXT,
            created_at INTEGER NOT NULL,
            session_key TEXT
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)")}
    if "session_key" not in cols:
        conn.execute("ALTER TABLE recommendations ADD COLUMN session_key TEXT")
    conn.commit()
    return conn


def store_recommendation(
    decision: FinalDecisionResult,
    drawings: list[ChartDrawing],
    market: AgentMarketContext,
    *,
    session_key: str | None = None,
) -> str:
    tradable, _reason = assess_plan_tradability(decision)
    if not tradable:
        return ""
    rec = decision.recommendation
    if not rec.entry or not rec.stop_loss or not rec.targets:
        return ""
    if session_key and latest_live_recommendation(session_key):
        return ""

    rec_id = str(uuid.uuid4())
    gate_json = None
    if decision.gate_chain:
        gate_json = json.dumps(
            [{"id": v.id, "status": v.status, "reason_ar": v.reason_ar} for v in decision.gate_chain.verdicts]
        )
    drawings_json = json.dumps(
        [
            {
                "type": d.type,
                "label": d.label,
                "color": d.color,
                "points": d.points,
                "meta": d.meta,
            }
            for d in drawings
        ]
    )
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO recommendations
            (id, symbol, interval, direction, entry, stop_loss, targets_json, status,
             summary, confidence, drawings_json, gate_json, created_at, session_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec_id,
                rec.symbol,
                rec.interval,
                rec.action,
                rec.entry,
                rec.stop_loss,
                json.dumps(rec.targets),
                rec.execution_state or "valid_now",
                decision.summary,
                decision.confidence,
                drawings_json,
                gate_json,
                int(time.time() * 1000),
                session_key,
            ),
        )
        conn.commit()
    from nanobot.trading.memory.decisions import record_trade_decision

    record_trade_decision(rec_id, decision, market, interval=rec.interval or "15m")
    return rec_id


def get_recommendation(rec_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, symbol, interval, direction, entry, stop_loss, targets_json, status, summary, confidence, created_at "
            "FROM recommendations WHERE id = ?",
            (rec_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "symbol": row[1],
        "interval": row[2],
        "direction": row[3],
        "entry": row[4],
        "stop_loss": row[5],
        "targets": json.loads(row[6] or "[]"),
        "status": row[7],
        "summary": row[8],
        "confidence": row[9],
        "created_at": row[10],
    }


def latest_live_recommendation(session_key: str | None) -> dict | None:
    """One live plan per conversation. session_key None → no conversation lock."""
    if not session_key:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, symbol, interval, direction, entry, stop_loss, targets_json, status, "
            "summary, confidence, created_at, session_key "
            "FROM recommendations WHERE session_key = ? AND status IN ('valid_now', 'awaiting_activation') "
            "ORDER BY created_at DESC LIMIT 1",
            (session_key,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "symbol": row[1],
        "interval": row[2],
        "direction": row[3],
        "entry": row[4],
        "stop_loss": row[5],
        "targets": json.loads(row[6] or "[]"),
        "status": row[7],
        "summary": row[8],
        "confidence": row[9],
        "created_at": row[10],
        "session_key": row[11],
    }


def list_recommendations(limit: int = 20) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, interval, direction, entry, stop_loss, targets_json, status, summary, confidence, created_at "
            "FROM recommendations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        out.append(
            {
                "id": row[0],
                "symbol": row[1],
                "interval": row[2],
                "direction": row[3],
                "entry": row[4],
                "stop_loss": row[5],
                "targets": json.loads(row[6] or "[]"),
                "status": row[7],
                "summary": row[8],
                "confidence": row[9],
                "created_at": row[10],
            }
        )
    return out
