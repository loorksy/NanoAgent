"""HITL MetaAPI propose/confirm never auto-sends."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.mt5_execution import mt5_confirm_order, mt5_propose_order
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
