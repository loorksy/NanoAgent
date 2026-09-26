"""Generic approval registry wrapping MT5 order proposals (and future confirmations)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict, cast

from loguru import logger

from nanobot.agent_api.db import Database, row_to_dict
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import (
    JsonObject,
    approval_data,
    notification_data,
    now_ms,
)
from nanobot.agent_api.hub import EventHub

ApprovalStatus = Literal["pending", "confirmed", "cancelled", "expired", "failed"]
ApprovalType = Literal["execution", "modify", "close", "generic"]
Decision = Literal["confirm", "cancel"]
DecisionFn = Callable[..., Awaitable[dict[str, object]]]


class ApprovalRecord(TypedDict):
    id: str
    session: str | None
    run: str | None
    type: ApprovalType
    status: ApprovalStatus
    summary: str
    created_at: int
    expires_at: int | None
    resolved_at: int | None
    decision: Decision | None
    source_id: str | None
    details: JsonObject


def _status(value: object) -> ApprovalStatus:
    if value in ("pending", "confirmed", "cancelled", "expired", "failed"):
        return value
    return "pending"


def _type(value: object) -> ApprovalType:
    if value in ("execution", "modify", "close", "generic"):
        return value
    return "generic"


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _row(row: sqlite3.Row) -> ApprovalRecord:
    record = row_to_dict(row)
    extra_raw = record.get("extra")
    details: JsonObject = {}
    if isinstance(extra_raw, str):
        parsed: object = json.loads(extra_raw)
        if isinstance(parsed, dict):
            details = cast(JsonObject, parsed)
    decision = record.get("decision")
    session = record.get("session")
    run = record.get("run")
    source = record.get("source_id")
    created = record.get("created_at")
    return {
        "id": str(record["id"]),
        "session": session if isinstance(session, str) else None,
        "run": run if isinstance(run, str) else None,
        "type": _type(record.get("type")),
        "status": _status(record.get("status")),
        "summary": str(record.get("summary") or ""),
        "created_at": created if isinstance(created, int) else 0,
        "expires_at": _int_or_none(record.get("expires_at")),
        "resolved_at": _int_or_none(record.get("resolved_at")),
        "decision": decision if decision in ("confirm", "cancel") else None,
        "source_id": source if isinstance(source, str) else None,
        "details": details,
    }


def proposal_summary(proposal: JsonObject) -> str:
    """Compact, locale-neutral description built only from proposal values."""
    return " ".join(
        str(proposal.get(key, ""))
        for key in ("side", "symbol")
    ).strip() + (
        f" lot={proposal.get('lot')} entry={proposal.get('entry')} stop={proposal.get('stop')}"
    )


async def _default_confirm(**kwargs: object) -> dict[str, object]:
    from nanobot.trading.mt5_execution import mt5_confirm_order

    proposal_id = str(kwargs.get("proposal_id") or "")
    return await mt5_confirm_order(proposal_id=proposal_id, confirm=True)


async def _default_cancel(**kwargs: object) -> dict[str, object]:
    from nanobot.trading.mt5_execution import mt5_cancel_order

    order_id = str(kwargs.get("order_id") or "")
    return await mt5_cancel_order(order_id=order_id, confirm=True)


class ApprovalRegistry:
    def __init__(
        self,
        db: Database,
        hub: EventHub,
        *,
        confirm_fn: DecisionFn | None = None,
        cancel_fn: DecisionFn | None = None,
    ) -> None:
        self._db = db
        self._hub = hub
        self._confirm = confirm_fn or _default_confirm
        self._cancel = cancel_fn or _default_cancel

    # -- creation ------------------------------------------------------------

    def open(
        self,
        *,
        type: ApprovalType,
        summary: str,
        session: str | None,
        run: str | None,
        expires_at: int | None,
        source_id: str | None,
        details: JsonObject | None = None,
        approval_id: str | None = None,
    ) -> ApprovalRecord:
        ident = approval_id or (f"ap_{source_id}" if source_id else f"ap_{now_ms()}")
        existing = self.get(ident)
        if existing is not None:
            return existing
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO approvals(id, session, run, type, status, summary, created_at, "
                "expires_at, source_id, extra) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
                (
                    ident,
                    session,
                    run,
                    type,
                    summary,
                    now_ms(),
                    expires_at,
                    source_id,
                    json.dumps(details or {}, ensure_ascii=False, default=str),
                ),
            )
        record = self.get(ident)
        assert record is not None
        if session is not None:
            self._hub.publish(
                session,
                "approval",
                approval_data(
                    ident,
                    type=type,
                    summary=summary,
                    expires_at=expires_at,
                    status="pending",
                ),
                run=run,
            )
            self._hub.approval_opened(session, ident)
        return record

    def open_from_proposal(
        self,
        proposal: JsonObject,
        *,
        session: str | None,
        run: str | None,
    ) -> ApprovalRecord | None:
        proposal_id = proposal.get("id")
        if not isinstance(proposal_id, str):
            return None
        if proposal.get("confirmed") or proposal.get("executed"):
            return None
        expires = proposal.get("expires_ms")
        return self.open(
            type="execution",
            summary=proposal_summary(proposal),
            session=session,
            run=run,
            expires_at=expires if isinstance(expires, int) else None,
            source_id=proposal_id,
            details={"proposal": dict(proposal)},
        )

    def sync_proposals(self) -> int:
        """Register proposals created by other channels (best effort, read-only)."""
        try:
            from nanobot.trading.mt5_proposals import get_proposal_store
        except Exception:
            return 0
        store = get_proposal_store()
        items = getattr(store, "_items", None)
        if not isinstance(items, dict):
            return 0
        added = 0
        for proposal in list(cast(dict[str, object], items).values()):
            to_public = getattr(proposal, "to_public", None)
            if not callable(to_public):
                continue
            public = cast(JsonObject, to_public())
            proposal_id = public.get("id")
            if not isinstance(proposal_id, str) or self.get(f"ap_{proposal_id}") is not None:
                continue
            if self.open_from_proposal(public, session=None, run=None) is not None:
                added += 1
        return added

    # -- queries -------------------------------------------------------------

    def get(self, approval_id: str) -> ApprovalRecord | None:
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,),
            ).fetchone()
        return _row(row) if row is not None else None

    def list(self, *, status: ApprovalStatus | None = None, limit: int = 100) -> list[ApprovalRecord]:
        with self._db.cursor() as cur:
            if status is None:
                rows = cur.execute(
                    "SELECT * FROM approvals ORDER BY created_at DESC LIMIT ?", (limit,),
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT * FROM approvals WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        return [_row(row) for row in rows]

    def pending_for_session(self, session: str) -> list[ApprovalRecord]:
        return [a for a in self.list(status="pending") if a["session"] == session]

    # -- decisions -----------------------------------------------------------

    async def decide(self, approval_id: str, decision: Decision) -> ApprovalRecord:
        record = self.get(approval_id)
        if record is None:
            raise ApiError(404, "approval_not_found")
        if record["status"] != "pending":
            raise ApiError(409, "approval_already_resolved", details={"status": record["status"]})
        if record["expires_at"] is not None and record["expires_at"] < now_ms():
            self._resolve(record, "expired", None)
            raise ApiError(410, "approval_expired")
        if decision == "confirm":
            result = await self._execute_confirm(record)
            if not result.get("ok"):
                raise ApiError(
                    409,
                    "approval_blocked",
                    str(result.get("reason_key") or "approval_blocked"),
                    {"result": result},
                )
            return self._resolve(record, "confirmed", "confirm", result=result)
        result = await self._execute_cancel(record)
        return self._resolve(record, "cancelled", "cancel", result=result)

    async def _execute_confirm(self, record: ApprovalRecord) -> dict[str, object]:
        if record["type"] == "execution" and record["source_id"]:
            return await self._confirm(proposal_id=record["source_id"])
        return {"ok": True}

    async def _execute_cancel(self, record: ApprovalRecord) -> dict[str, object]:
        proposal = record["details"].get("proposal")
        if isinstance(proposal, dict):
            proposal_map = cast(JsonObject, proposal)
            position_id = proposal_map.get("position_id")
            if (
                proposal_map.get("executed")
                and isinstance(position_id, str)
                and proposal_map.get("order_type") in ("limit", "stop")
            ):
                try:
                    return await self._cancel(order_id=position_id)
                except Exception:
                    logger.exception("agent_api broker cancel failed for {}", record["id"])
                    return {"ok": False, "reason_key": "mt5.broker_send_failed"}
        return {"ok": True}

    def _resolve(
        self,
        record: ApprovalRecord,
        status: ApprovalStatus,
        decision: Decision | None,
        *,
        result: dict[str, object] | None = None,
    ) -> ApprovalRecord:
        details = dict(record["details"])
        if result is not None:
            details["result"] = result
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE approvals SET status = ?, decision = ?, resolved_at = ?, extra = ? "
                "WHERE id = ?",
                (
                    status,
                    decision,
                    now_ms(),
                    json.dumps(details, ensure_ascii=False, default=str),
                    record["id"],
                ),
            )
        updated = self.get(record["id"])
        assert updated is not None
        session = record["session"]
        if session is not None:
            self._hub.publish(
                session,
                "approval",
                approval_data(
                    record["id"],
                    type=record["type"],
                    summary=record["summary"],
                    expires_at=record["expires_at"],
                    status=status,
                    actions=(),
                ),
                run=record["run"],
            )
            outcome: Literal["ok", "cancelled", "expired"]
            if status == "confirmed":
                outcome = "ok"
            elif status == "expired":
                outcome = "expired"
                self._hub.publish(
                    session,
                    "notification",
                    notification_data(
                        "warning",
                        "approval.expired.title",
                        "approval.expired.body",
                        args={"approval_id": record["id"]},
                    ),
                    run=record["run"],
                )
            else:
                outcome = "cancelled"
            self._hub.approval_resolved(session, record["id"], outcome=outcome)
        return updated

    def expire_due(self, *, now: int | None = None) -> list[ApprovalRecord]:
        current = now_ms() if now is None else now
        expired: list[ApprovalRecord] = []
        for record in self.list(status="pending"):
            if record["expires_at"] is not None and record["expires_at"] < current:
                expired.append(self._resolve(record, "expired", None))
        return expired
