"""HITL MetaAPI propose/confirm never auto-sends."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.intel.tickets import TicketStore
from nanobot.trading.mt5_execution import (
    mt5_close_position,
    mt5_confirm_order,
    mt5_get_account,
    mt5_modify_order,
    mt5_propose_order,
)
from nanobot.trading.mt5_metaapi import NullTransport, set_transport_for_tests
from nanobot.trading.mt5_proposals import get_proposal_store

SAFE_TS = datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp()


class RecordingTransport(NullTransport):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[dict] = []
        self.closed: list[dict] = []
        self.cancelled: list[dict] = []

    async def account_snapshot(self) -> dict:
        return {"ok": True, "account": {"balance": 10_000, "equity": 10_000, "marginLevel": 900}}

    async def quote(self, symbol: str) -> dict:
        return {"ok": True, "quote": {"bid": 2650.0, "ask": 2650.12}}

    async def send_market(self, payload: dict) -> dict:
        self.sent.append(payload)
        return {"ok": True, "result": {"positionId": "ticket-1"}}

    async def open_positions(self) -> list[dict]:
        return [
            {
                "id": "ticket-1",
                "symbol": "XAUUSD",
                "type": "buy",
                "openPrice": 2650.0,
                "stopLoss": 2640.0,
                "takeProfit": 2670.0,
                "time": SAFE_TS - 60,
            }
        ]

    async def open_orders(self) -> list[dict]:
        return [{"id": "pend-1", "symbol": "XAUUSD"}]

    async def modify_position(self, payload: dict) -> dict:
        self.sent.append({"modify": payload})
        return {"ok": True, "result": payload}

    async def close_position(self, payload: dict) -> dict:
        self.closed.append(payload)
        self.sent.append({"close": payload})
        return {"ok": True, "result": payload}

    async def cancel_order(self, payload: dict) -> dict:
        self.cancelled.append(payload)
        return {"ok": True, "result": payload}


@pytest.fixture(autouse=True)
def _transport(monkeypatch: pytest.MonkeyPatch):
    rec = RecordingTransport()
    set_transport_for_tests(rec)
    monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: SAFE_TS)
    monkeypatch.setattr("nanobot.trading.mt5_proposals.time.time", lambda: SAFE_TS)
    yield rec
    set_transport_for_tests(None)


@pytest.mark.asyncio
async def test_propose_does_not_send( _transport: RecordingTransport):
    out = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0, 2680.0],
        lot=0.1,
    )
    assert out["executed"] is False
    assert out["operator_must_confirm"] is True
    assert _transport.sent == []
    assert get_proposal_store().get(out["proposal"]["id"]) is not None


@pytest.mark.asyncio
async def test_confirm_false_never_sends(_transport: RecordingTransport):
    proposed = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0],
        lot=0.1,
    )
    pid = proposed["proposal"]["id"]
    out = await mt5_confirm_order(proposal_id=pid, confirm=False)
    assert out["ok"] is False
    assert out["executed"] is False
    assert out["blocked_by"] == "hitl"
    assert _transport.sent == []


@pytest.mark.asyncio
async def test_confirm_true_sends_once(_transport: RecordingTransport):
    proposed = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0],
        lot=0.1,
    )
    pid = proposed["proposal"]["id"]
    out = await mt5_confirm_order(proposal_id=pid, confirm=True)
    assert out["ok"] is True
    assert out["executed"] is True
    assert len(_transport.sent) == 1


@pytest.mark.asyncio
async def test_modify_without_confirm_never_sends(_transport: RecordingTransport):
    out = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=False)
    assert out["executed"] is False
    assert _transport.sent == []


@pytest.mark.asyncio
async def test_modify_blocks_widening_stop(_transport: RecordingTransport):
    out = await mt5_modify_order(position_id="ticket-1", stop=2630.0, confirm=True)
    assert out["ok"] is False
    assert out["blocked_by"] == "no_widen"
    assert _transport.sent == []


@pytest.mark.asyncio
async def test_account_includes_management_snapshot(_transport: RecordingTransport):
    out = await mt5_get_account()
    assert out["ok"] is True
    assert out["management"] is not None
    assert "trailing_stop" in out["management"]
    assert out["flatten_required"] is False
    assert out["adopt_candidates"]


@pytest.mark.asyncio
async def test_confirm_persists_ticket_and_clears_adopt(_transport: RecordingTransport, tmp_path):
    proposed = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0],
        lot=0.1,
    )
    out = await mt5_confirm_order(proposal_id=proposed["proposal"]["id"], confirm=True)
    assert out["executed"] is True
    stored = TicketStore().get("ticket-1")
    assert stored is not None
    assert stored.managed is True
    account = await mt5_get_account()
    assert account["adopt_candidates"] == []
    assert account["tickets"][0]["ticket_id"] == "ticket-1"


@pytest.mark.asyncio
async def test_flatten_all_requires_confirm(_transport: RecordingTransport):
    denied = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=False)
    assert denied["executed"] is False
    assert _transport.closed == []
    out = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=True)
    assert out["flatten"] is True
    assert out["executed"] is True
    assert _transport.closed
    assert _transport.cancelled


@pytest.mark.asyncio
async def test_adopt_manual_ticket(_transport: RecordingTransport):
    out = await mt5_get_account(adopt_ticket="ticket-1")
    assert out["ok"] is True
    assert out["adopt_candidates"] == []
    stored = TicketStore().get("ticket-1")
    assert stored is not None
    assert stored.adopted is True


class FailingSendTransport(RecordingTransport):
    async def send_market(self, payload: dict) -> dict:
        self.sent.append(payload)
        return {"ok": False, "error": "rejected"}

    async def modify_position(self, payload: dict) -> dict:
        self.sent.append({"modify": payload})
        return {"ok": False, "error": "modify-rejected"}

    async def close_position(self, payload: dict) -> dict:
        self.closed.append(payload)
        return {"ok": False, "error": "close-rejected"}

    async def cancel_order(self, payload: dict) -> dict:
        self.cancelled.append(payload)
        return {"ok": False, "error": "cancel-rejected"}


@pytest.mark.asyncio
async def test_failed_send_does_not_mark_executed_or_open_ticket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    rec = FailingSendTransport()
    set_transport_for_tests(rec)
    tickets = TicketStore(tmp_path / "tickets.sqlite")
    monkeypatch.setattr("nanobot.trading.mt5_execution.TicketStore", lambda: tickets)
    monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: SAFE_TS)
    monkeypatch.setattr("nanobot.trading.mt5_proposals.time.time", lambda: SAFE_TS)
    proposed = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0],
        lot=0.1,
    )
    pid = proposed["proposal"]["id"]
    out = await mt5_confirm_order(proposal_id=pid, confirm=True)
    assert rec.sent
    assert out["ok"] is False
    assert out["executed"] is False
    assert out["reason_key"] == "mt5.broker_send_failed"
    stored = get_proposal_store().get(pid)
    assert stored is not None
    assert stored.executed is False
    assert tickets.get("ticket-1") is None
    set_transport_for_tests(None)


@pytest.mark.asyncio
async def test_failed_modify_close_cancel_are_not_false_success(
    monkeypatch: pytest.MonkeyPatch,
):
    rec = FailingSendTransport()
    set_transport_for_tests(rec)
    monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: SAFE_TS)
    from nanobot.trading.mt5_execution import mt5_cancel_order

    modified = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=True)
    assert modified["ok"] is False
    assert modified["executed"] is False
    closed = await mt5_close_position(position_id="ticket-1", confirm=True)
    assert closed["ok"] is False
    assert closed["executed"] is False
    cancelled = await mt5_cancel_order(order_id="pend-1", confirm=True)
    assert cancelled["ok"] is False
    assert cancelled["executed"] is False
    flatten = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=True)
    assert flatten["ok"] is False
    assert flatten["executed"] is False
    set_transport_for_tests(None)


@pytest.mark.asyncio
async def test_expired_proposal_cannot_confirm(
    _transport: RecordingTransport,
    monkeypatch: pytest.MonkeyPatch,
):
    proposed = await mt5_propose_order(
        side="buy",
        entry=2650.0,
        stop=2640.0,
        targets=[2670.0],
        lot=0.1,
    )
    pid = proposed["proposal"]["id"]
    later = SAFE_TS + 10_000
    monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: later)
    out = await mt5_confirm_order(proposal_id=pid, confirm=True)
    assert out["ok"] is False
    assert out["executed"] is False
    assert out["blocked_by"] == "proposal_ttl"
    assert _transport.sent == []
