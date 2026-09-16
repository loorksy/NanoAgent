"""HITL MetaAPI propose/confirm never auto-sends."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.mt5_execution import (
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
        super().__init__(reason="test")
        self.sent: list[dict] = []

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

    async def modify_position(self, payload: dict) -> dict:
        self.sent.append({"modify": payload})
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
