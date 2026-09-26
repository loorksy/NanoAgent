"""Structured results (07 §5): schema validation and SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from functools import cache
from pathlib import Path
from typing import Literal, TypedDict, cast

from nanobot.agent.tools.base import Schema
from nanobot.agent_api.db import Database, row_to_dict
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import JsonObject, now_ms
from nanobot.agent_api.ids import new_id

ResultType = Literal[
    "market",
    "analysis",
    "scenarios",
    "risk",
    "decision",
    "approval",
    "plan_status",
    "scorecard",
]
RESULT_TYPES: tuple[ResultType, ...] = (
    "market",
    "analysis",
    "scenarios",
    "risk",
    "decision",
    "approval",
    "plan_status",
    "scorecard",
)
SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


class ResultRecord(TypedDict):
    id: str
    session: str | None
    run: str | None
    type: ResultType
    ts: int
    payload: JsonObject


def is_result_type(value: object) -> bool:
    return isinstance(value, str) and value in RESULT_TYPES


@cache
def load_schema(result_type: str) -> dict[str, object]:
    path = SCHEMAS_DIR / f"{result_type}.json"
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"schema {path} must be a JSON object")
    return cast(dict[str, object], raw)


def validate_payload(result_type: str, payload: object) -> list[str]:
    """Return validation errors (empty when valid) using the in-repo JSON Schema subset."""
    if not is_result_type(result_type):
        return [f"unknown result type {result_type!r}"]
    if not isinstance(payload, dict):
        return ["payload should be object"]
    schema = load_schema(result_type)
    return Schema.validate_json_schema_value(payload, schema, "")


def _row(row: sqlite3.Row) -> ResultRecord:
    record = row_to_dict(row)
    payload_raw = record.get("payload")
    payload: JsonObject = {}
    if isinstance(payload_raw, str):
        parsed: object = json.loads(payload_raw)
        if isinstance(parsed, dict):
            payload = cast(JsonObject, parsed)
    session = record.get("session")
    run = record.get("run")
    ts = record.get("ts")
    return {
        "id": str(record["id"]),
        "session": session if isinstance(session, str) else None,
        "run": run if isinstance(run, str) else None,
        "type": cast(ResultType, str(record.get("type"))),
        "ts": ts if isinstance(ts, int) else 0,
        "payload": payload,
    }


class ResultsStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def put(
        self,
        result_type: str,
        payload: JsonObject,
        *,
        session: str | None,
        run: str | None,
    ) -> ResultRecord:
        errors = validate_payload(result_type, payload)
        if errors:
            raise ApiError(400, "invalid_result", details={"type": result_type, "errors": errors})
        result_id = new_id("res_")
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO results(id, session, run, type, ts, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    result_id,
                    session,
                    run,
                    result_type,
                    now_ms(),
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )
        record = self.get(result_id)
        assert record is not None
        return record

    def get(self, result_id: str) -> ResultRecord | None:
        with self._db.cursor() as cur:
            row = cur.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
        return _row(row) if row is not None else None

    def list(self, *, session: str | None = None, limit: int = 50) -> list[ResultRecord]:
        with self._db.cursor() as cur:
            if session is None:
                rows = cur.execute(
                    "SELECT * FROM results ORDER BY id DESC LIMIT ?", (limit,),
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT * FROM results WHERE session = ? ORDER BY id DESC LIMIT ?",
                    (session, limit),
                ).fetchall()
        return [_row(row) for row in rows]
