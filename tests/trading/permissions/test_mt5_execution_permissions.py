"""mt5_propose/modify/close honour the MT5 permission level (08 §4.2, §8)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from nanobot.config.loader import save_config
from nanobot.config.schema import Config
from nanobot.security.secret_store import SecretStore
from nanobot.trading.mt5_execution import (
    mt5_close_position,
    mt5_confirm_order,
    mt5_modify_order,
    mt5_propose_order,
)
from nanobot.trading.mt5_metaapi import NullTransport, set_transport_for_tests
from nanobot.trading.mt5_proposals import get_proposal_store
from nanobot.trading.permissions.model import Mt5Permissions
from nanobot.trading.permissions.store import PermissionStore, set_permission_store_for_tests
from nanobot.trading.risk_state import RiskStateStore
from nanobot.trading.runtime_state import TradingRuntimeStore

SAFE_TS = datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp()  # london + newyork
DEAD_TS = datetime(2023, 11, 15, 22, 30, tzinfo=UTC).timestamp()  # no session
GRANTED_S = int(SAFE_TS) - 2 * 86_400


class RecordingTransport(NullTransport):
    def __init__(self, *, spread: float = 0.12, volume: float = 0.1) -> None:
        super().__init__()
        self.spread = spread
        self.volume = volume
        self.sent: list[dict] = []
        self.closed: list[dict] = []
        self.cancelled: list[dict] = []

    async def account_snapshot(self) -> dict:
        return {"ok": True, "account": {"balance": 10_000, "equity": 10_000, "marginLevel": 900}}

    async def quote(self, symbol: str) -> dict:
        return {"ok": True, "quote": {"bid": 2650.0, "ask": 2650.0 + self.spread}}

    async def send_market(self, payload: dict) -> dict:
        self.sent.append(payload)
        return {"ok": True, "result": {"positionId": "ticket-1"}}

    async def open_positions(self) -> list[dict]:
        return [
            {
                "id": "ticket-1",
                "symbol": "XAUUSD",
                "type": "buy",
                "volume": self.volume,
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


class Harness:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch
        self.transport = RecordingTransport()
        set_transport_for_tests(self.transport)
        config_path = tmp_path / "config.json"
        save_config(Config(), config_path)
        monkeypatch.setattr("nanobot.config.loader._current_config_path", config_path)
        self.runtime = TradingRuntimeStore(tmp_path / "runtime.json")
        self.runtime.update(paper_mode=False)
        self.risk = RiskStateStore(tmp_path / "risk.json")
        monkeypatch.setattr("nanobot.trading.mt5_execution.get_runtime_store", lambda: self.runtime)
        monkeypatch.setattr("nanobot.trading.mt5_execution.get_risk_store", lambda: self.risk)
        self.permissions = PermissionStore(SecretStore(tmp_path / "secrets.enc"))
        set_permission_store_for_tests(self.permissions)
        self.set_time(SAFE_TS)

    def set_time(self, ts: float) -> None:
        self.monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: ts)
        self.monkeypatch.setattr("nanobot.trading.mt5_proposals.time.time", lambda: ts)

    def grant(self, **overrides: object) -> Mt5Permissions:
        base: dict[str, object] = {
            "level": "execute",
            "can_open": True,
            "granted_at": GRANTED_S,
            "granted_by": "web-1",
        }
        base.update(overrides)
        perms = Mt5Permissions.model_validate(base)
        self.permissions.save(perms, who="test", now_s=SAFE_TS)
        return perms

    def set_level(self, level: str) -> None:
        self.permissions.save(Mt5Permissions(level=level), who="test", now_s=SAFE_TS)  # type: ignore[arg-type]


@pytest.fixture
def h(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    harness = Harness(tmp_path, monkeypatch)
    yield harness
    set_transport_for_tests(None)
    set_permission_store_for_tests(None)


async def _propose(lot: float = 0.3) -> dict:
    return await mt5_propose_order(
        side="buy", entry=2650.0, stop=2640.0, targets=[2670.0], lot=lot
    )


# -- level 0: recommend --------------------------------------------------------


async def test_recommend_denies_propose_modify_close_without_touching_broker(h: Harness) -> None:
    h.set_level("recommend")
    out = await _propose()
    assert out["ok"] is False
    assert out["executed"] is False
    assert out["reason_key"] == "permission.level_recommend_only"
    assert out["permission_level"] == "recommend"
    assert "proposal" not in out
    modified = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=True)
    assert modified["ok"] is False
    assert modified["reason_key"] == "permission.level_recommend_only"
    closed = await mt5_close_position(position_id="ticket-1", confirm=True)
    assert closed["ok"] is False
    assert closed["reason_key"] == "permission.level_recommend_only"
    flat = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=True)
    assert flat["reason_key"] == "permission.level_recommend_only"
    assert h.transport.sent == []
    assert h.transport.closed == []


# -- level 1: propose (default) ----------------------------------------------


async def test_default_propose_level_keeps_hitl_behaviour(h: Harness) -> None:
    out = await _propose(lot=0.1)
    assert out["status"] == "proposed"
    assert out["executed"] is False
    assert out["operator_must_confirm"] is True
    assert out["permission_level"] == "propose"
    assert out["permission"]["mode"] == "propose"
    assert "auto_confirmed" not in out
    assert h.transport.sent == []
    confirmed = await mt5_confirm_order(proposal_id=out["proposal"]["id"], confirm=True)
    assert confirmed["executed"] is True
    assert confirmed["proposal"]["confirmed_by"] == "operator"
    assert confirmed["proposal"]["auto_confirmed"] is False
    modify = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=False)
    assert modify["reason_key"] == "mt5.confirm_required_modify"
    close = await mt5_close_position(position_id="ticket-1", confirm=False)
    assert close["reason_key"] == "mt5.confirm_required_close"
    assert len(h.transport.sent) == 1


async def test_propose_level_flags_lot_above_cap_as_warning(h: Harness) -> None:
    h.permissions.save(Mt5Permissions(max_lot_per_order=0.1), who="test", now_s=SAFE_TS)
    out = await _propose(lot=0.3)
    assert out["status"] == "proposed"
    assert out["proposal"]["lot"] == 0.3
    assert out["permission"]["warnings"] == ["permission.lot_exceeds_cap"]


# -- level 2: execute ---------------------------------------------------------


async def test_execute_auto_confirms_with_capped_lot(h: Harness) -> None:
    h.grant(max_lot_per_order=0.1, max_total_lots=0.0)
    out = await _propose(lot=0.3)
    assert out["ok"] is True
    assert out["status"] == "executed"
    assert out["executed"] is True
    assert out["auto_confirmed"] is True
    assert out["operator_must_confirm"] is False
    assert out["permission_level"] == "execute"
    assert out["confirmed_by"] == "permission:web-1"
    assert out["permission"]["adjusted_lot"] == 0.1
    assert out["permission"]["reason_key"] == "permission.lot_capped"
    assert out["display"]["lot"] == 0.1
    assert len(h.transport.sent) == 1
    assert h.transport.sent[0]["lot"] == 0.1
    assert h.transport.sent[0]["comment"] == "AUTO_PERMISSION"
    stored = get_proposal_store().get(out["proposal"]["id"])
    assert stored is not None
    assert stored.confirmed is True
    assert stored.executed is True
    assert stored.confirmed_by == "permission:web-1"
    assert stored.auto_confirmed is True
    assert stored.extra["requested_lot"] == 0.3


async def test_execute_hard_cap_rejects_without_sending(h: Harness) -> None:
    h.grant(max_lot_per_order=0.1, max_lot_hard=True)
    out = await _propose(lot=0.3)
    assert out["ok"] is False
    assert out["reason_key"] == "permission.lot_exceeds_hard_cap"
    assert "proposal" not in out
    assert h.transport.sent == []


async def test_execute_respects_total_lots_including_open_positions(h: Harness) -> None:
    h.transport.volume = 0.3
    h.grant(max_lot_per_order=1.0, max_total_lots=0.4)
    out = await _propose(lot=0.3)
    assert out["status"] == "executed"
    assert out["permission"]["adjusted_lot"] == 0.1
    assert h.transport.sent[0]["lot"] == 0.1
    h.transport.volume = 0.4
    full = await _propose(lot=0.1)
    assert full["status"] == "proposed"
    assert full["permission"]["downgrade_reason_key"] == "permission.total_lots_reached"
    assert len(h.transport.sent) == 1


@pytest.mark.parametrize(
    ("overrides", "ts", "reason"),
    [
        ({}, DEAD_TS, "permission.outside_session"),
        ({"granted_at": int(SAFE_TS) - 3_600}, SAFE_TS, "permission.grace_period"),
        ({"expires_at": int(SAFE_TS) - 1}, SAFE_TS, "permission.expired"),
    ],
)
async def test_execute_downgrades_to_propose(
    h: Harness, overrides: dict[str, object], ts: float, reason: str
) -> None:
    h.grant(**overrides)
    h.set_time(ts)
    out = await _propose(lot=0.1)
    assert out["ok"] is True
    assert out["status"] == "proposed"
    assert out["operator_must_confirm"] is True
    assert out["permission_level"] == "execute"
    assert out["permission"]["mode"] == "propose"
    assert out["permission"]["effective_level"] == "propose"
    assert out["permission"]["downgrade_reason_key"] == reason
    assert h.transport.sent == []


async def test_kill_switch_and_pause_block_auto_execution(h: Harness) -> None:
    h.grant()
    h.runtime.update(kill_switch=True)
    out = await _propose(lot=0.1)
    assert out["status"] == "proposed"
    assert out["permission"]["downgrade_reason_key"] == "permission.kill_switch"
    h.runtime.update(kill_switch=False, paused=True)
    paused = await _propose(lot=0.1)
    assert paused["permission"]["downgrade_reason_key"] == "permission.paused"
    assert h.transport.sent == []


async def test_daily_loss_ceiling_downgrades(h: Harness) -> None:
    h.grant()
    h.risk.update(daily_pnl_pct=-2.0)
    out = await _propose(lot=0.1)
    assert out["status"] == "proposed"
    assert out["permission"]["downgrade_reason_key"] == "permission.daily_loss_ceiling"
    assert h.transport.sent == []


async def test_paper_mode_note_travels_with_execution(h: Harness) -> None:
    h.runtime.update(paper_mode=True)
    h.grant()
    out = await _propose(lot=0.1)
    assert out["status"] == "executed"
    assert "permission.paper_mode" in out["permission"]["notes"]


async def test_execute_still_runs_every_gate(h: Harness) -> None:
    h.transport.spread = 1.0  # 100 points: over SPREAD_MAX_POINTS, RR still >= 1.5 live
    h.grant()
    out = await _propose(lot=0.1)
    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert out["auto_confirmed"] is False
    assert out["operator_must_confirm"] is True
    assert out["blocked_by"] == "spread"
    assert out["proposal"]["confirmed"] is False
    assert h.transport.sent == []


async def test_execute_modify_tighten_without_confirm(h: Harness) -> None:
    h.grant()
    out = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=False)
    assert out["ok"] is True
    assert out["executed"] is True
    assert out["auto_confirmed"] is True
    assert out["confirmed_by"] == "permission:web-1"
    assert out["permission"]["action"] == "modify_sl_tp"
    assert h.transport.sent == [{"modify": {"position_id": "ticket-1", "stop": 2642.0, "take_profit": None}}]


async def test_execute_modify_scope_and_widen_rules(h: Harness) -> None:
    h.grant(can_modify_sl_tp=False)
    denied = await mt5_modify_order(position_id="ticket-1", stop=2642.0, confirm=False)
    assert denied["ok"] is False
    assert denied["reason_key"] == "mt5.confirm_required_modify"
    assert denied["auto_confirmed"] is False
    assert denied["permission"]["downgrade_reason_key"] == "permission.scope_not_granted"

    h.grant()
    widen = await mt5_modify_order(position_id="ticket-1", stop=2630.0, confirm=False)
    assert widen["reason_key"] == "mt5.confirm_required_modify"
    assert widen["permission"]["action"] == "widen_stop"
    assert widen["permission"]["downgrade_reason_key"] == "permission.scope_not_granted"

    h.grant(allow_widen_stop=True)
    gated = await mt5_modify_order(position_id="ticket-1", stop=2630.0, confirm=False)
    assert gated["ok"] is False
    assert gated["blocked_by"] == "no_widen"
    assert h.transport.sent == []


async def test_execute_close_partial_and_all(h: Harness) -> None:
    h.grant()
    partial = await mt5_close_position(position_id="ticket-1", confirm=False)
    assert partial["executed"] is True
    assert partial["auto_confirmed"] is True
    assert partial["permission"]["action"] == "partial_close"
    assert h.transport.closed == [{"position_id": "ticket-1"}]

    flat_denied = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=False)
    assert flat_denied["ok"] is False
    assert flat_denied["reason_key"] == "mt5.confirm_required_close"
    assert flat_denied["permission"]["downgrade_reason_key"] == "permission.scope_not_granted"
    assert h.transport.cancelled == []

    h.grant(can_close_all=True)
    flat = await mt5_close_position(position_id="ALL", flatten_all=True, confirm=False)
    assert flat["flatten"] is True
    assert flat["executed"] is True
    assert flat["auto_confirmed"] is True
    assert flat["permission"]["action"] == "close_all"
    assert h.transport.cancelled


async def test_human_confirm_at_execute_level_is_recorded_as_operator(h: Harness) -> None:
    h.grant(can_open=False)
    out = await _propose(lot=0.1)
    assert out["status"] == "proposed"
    assert out["permission"]["downgrade_reason_key"] == "permission.scope_not_granted"
    confirmed = await mt5_confirm_order(proposal_id=out["proposal"]["id"], confirm=True)
    assert confirmed["executed"] is True
    assert confirmed["proposal"]["confirmed_by"] == "operator"
    assert confirmed["proposal"]["auto_confirmed"] is False
    closed = await mt5_close_position(position_id="ticket-1", confirm=True)
    assert closed["executed"] is True
    assert "auto_confirmed" not in closed
