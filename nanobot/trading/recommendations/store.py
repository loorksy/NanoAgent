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
    if "closed_at" not in cols:
        conn.execute("ALTER TABLE recommendations ADD COLUMN closed_at INTEGER")
    if "close_reason" not in cols:
        conn.execute("ALTER TABLE recommendations ADD COLUMN close_reason TEXT")
    if "archive_category" not in cols:
        conn.execute("ALTER TABLE recommendations ADD COLUMN archive_category TEXT")
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
            "summary, confidence, created_at, session_key, gate_json "
            "FROM recommendations WHERE session_key = ? "
            "AND status IN ('valid_now', 'awaiting_activation', 'waiting', 'in_trade') "
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
        "gate_json": row[12],
    }


def close_live_recommendation(
    rec_id: str,
    *,
    status: str = "superseded",
    reason: str = "",
) -> bool:
    """Close an active recommendation (superseded, invalidated, etc.)."""
    now_ms = int(time.time() * 1000)
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE recommendations SET status = ?, closed_at = ?, close_reason = ? "
            "WHERE id = ? "
            "AND status IN ('valid_now', 'awaiting_activation', 'waiting', 'in_trade')",
            (status, now_ms, reason or status, rec_id),
        )
        conn.commit()
    return cur.rowcount > 0


def archive_recommendation(
    rec_id: str,
    *,
    category: str,
    reason: str = "",
) -> bool:
    """Tag a closed recommendation with an archive bucket for history views."""
    now_ms = int(time.time() * 1000)
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE recommendations SET archive_category = ?, closed_at = COALESCE(closed_at, ?), "
            "close_reason = COALESCE(NULLIF(close_reason, ''), ?) WHERE id = ?",
            (category, now_ms, reason or category, rec_id),
        )
        conn.commit()
    return cur.rowcount > 0


def update_recommendation_status(rec_id: str, status: str) -> bool:
    from nanobot.trading.recommendations.state_machine import CLOSED_OUTCOME_STATUSES

    now_ms = int(time.time() * 1000)
    with _conn() as conn:
        if status in CLOSED_OUTCOME_STATUSES:
            cur = conn.execute(
                "UPDATE recommendations SET status = ?, closed_at = COALESCE(closed_at, ?), "
                "close_reason = COALESCE(NULLIF(close_reason, ''), ?) WHERE id = ?",
                (status, now_ms, status, rec_id),
            )
        else:
            cur = conn.execute(
                "UPDATE recommendations SET status = ? WHERE id = ?",
                (status, rec_id),
            )
        conn.commit()
    return cur.rowcount > 0


def _row_to_dict(row: tuple) -> dict:
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
        "session_key": row[11] if len(row) > 11 else None,
        "closed_at": row[12] if len(row) > 12 else None,
        "close_reason": row[13] if len(row) > 13 else None,
        "archive_category": row[14] if len(row) > 14 else None,
    }


def list_recommendations(limit: int = 20) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, interval, direction, entry, stop_loss, targets_json, status, "
            "summary, confidence, created_at, session_key, closed_at, close_reason, archive_category "
            "FROM recommendations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_archived_recommendations(
    session_key: str,
    *,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    query = (
        "SELECT id, symbol, interval, direction, entry, stop_loss, targets_json, status, "
        "summary, confidence, created_at, session_key, closed_at, close_reason, archive_category "
        "FROM recommendations WHERE session_key = ? AND archive_category IS NOT NULL "
    )
    params: list[object] = [session_key]
    if category:
        query += "AND archive_category = ? "
        params.append(category)
    query += "ORDER BY COALESCE(closed_at, created_at) DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]
