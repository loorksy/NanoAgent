"""evaluate_permission: deny / propose / execute, lot capping, auto-downgrades (08 §4, §8)."""

from __future__ import annotations

import pytest

from mokli.config.schema import TradingRiskParameters
from mokli.trading.permissions.evaluate import (
    REASON_DAILY_LOSS,
    REASON_EXECUTED,
    REASON_EXPIRED,
    REASON_GRACE,
    REASON_KILL_SWITCH,
    REASON_LOT_CAPPED,
    REASON_LOT_EXCEEDS,
    REASON_LOT_HARD_CAP,
    REASON_NEWS_LOCK,
    REASON_OUTSIDE_SESSION,
    REASON_PAPER_MODE,
    REASON_PAUSED,
    REASON_PROPOSE,
    REASON_RECOMMEND_ONLY,
    REASON_SCOPE_NOT_GRANTED,
    REASON_TOTAL_LOTS,
    REASON_UNKNOWN_ACTION,
    PermissionContext,
    evaluate_permission,
)
from mokli.trading.permissions.model import ACTIONS, Mt5Permissions
from mokli.trading.risk_profiles import apply_profile

DAY0_MS = 1_700_006_400_000  # 2023-11-15 00:00 UTC
HOUR_MS = 3_600_000
LONDON_NY_MS = DAY0_MS + 13 * HOUR_MS
ASIA_MS = DAY0_MS + 3 * HOUR_MS
DEAD_MS = DAY0_MS + 22 * HOUR_MS
GRANTED_S = (DAY0_MS // 1000) - 2 * 86_400


def _exec(**overrides: object) -> Mt5Permissions:
    base: dict[str, object] = {
        "level": "execute",
        "can_open": True,
        "granted_at": GRANTED_S,
        "granted_by": "web-1",
        "grace_hours": 24,
    }
    base.update(overrides)
    return Mt5Permissions.model_validate(base)


def _ctx(perms: Mt5Permissions, **overrides: object) -> PermissionContext:
    base: dict[str, object] = {
        "permissions": perms,
        "now_ms": LONDON_NY_MS,
        "risk_params": apply_profile(TradingRiskParameters(), "balanced"),
        "paper_mode": False,
    }
    base.update(overrides)
    return PermissionContext(**base)  # type: ignore[arg-type]


# -- level 0 / 1 -------------------------------------------------------------


@pytest.mark.parametrize("action", ACTIONS)
def test_recommend_denies_every_action(action: str) -> None:
    d = evaluate_permission(action, _ctx(Mt5Permissions(level="recommend")))
    assert d.mode == "deny"
    assert d.reason_key == REASON_RECOMMEND_ONLY
    assert d.effective_level == "recommend"


def test_unknown_action_denied() -> None:
    d = evaluate_permission("teleport", _ctx(_exec()))
    assert d.mode == "deny"
    assert d.reason_key == REASON_UNKNOWN_ACTION


@pytest.mark.parametrize("action", ACTIONS)
def test_propose_level_always_proposes(action: str) -> None:
    d = evaluate_permission(action, _ctx(Mt5Permissions(), kill_switch=True, paused=True))
    assert d.mode == "propose"
    assert d.reason_key == REASON_PROPOSE
    assert d.downgrade_reason_key is None
    assert d.adjusted_lot is None


def test_propose_level_warns_when_lot_exceeds_cap() -> None:
    d = evaluate_permission("open", _ctx(Mt5Permissions(max_lot_per_order=0.1), requested_lot=0.3))
    assert d.mode == "propose"
    assert d.warnings == (REASON_LOT_EXCEEDS,)
    ok = evaluate_permission("open", _ctx(Mt5Permissions(max_lot_per_order=0.1), requested_lot=0.1))
    assert ok.warnings == ()


def test_paper_mode_note_is_attached() -> None:
    d = evaluate_permission("open", _ctx(Mt5Permissions(), paper_mode=True))
    assert REASON_PAPER_MODE in d.notes
    e = evaluate_permission("open", _ctx(_exec(), paper_mode=True))
    assert e.mode == "propose"
    assert e.downgrade_reason_key == REASON_PAPER_MODE
    assert REASON_PAPER_MODE in e.notes
    assert REASON_PAPER_MODE not in evaluate_permission("open", _ctx(_exec())).notes


# -- level 2 happy path -------------------------------------------------------


def test_execute_within_grant() -> None:
    d = evaluate_permission("open", _ctx(_exec(), requested_lot=0.1))
    assert d.mode == "execute"
    assert d.reason_key == REASON_EXECUTED
    assert d.adjusted_lot is None
    assert d.granted_by == "web-1"
    assert d.effective_level == "execute"


def test_execute_caps_lot_to_max_per_order() -> None:
    d = evaluate_permission("open", _ctx(_exec(max_lot_per_order=0.1), requested_lot=0.3))
    assert d.mode == "execute"
    assert d.reason_key == REASON_LOT_CAPPED
    assert d.adjusted_lot == 0.1


def test_execute_hard_cap_denies() -> None:
    d = evaluate_permission(
        "open", _ctx(_exec(max_lot_per_order=0.1, max_lot_hard=True), requested_lot=0.3)
    )
    assert d.mode == "deny"
    assert d.reason_key == REASON_LOT_HARD_CAP
    ok = evaluate_permission(
        "open", _ctx(_exec(max_lot_per_order=0.1, max_lot_hard=True), requested_lot=0.1)
    )
    assert ok.mode == "execute"


def test_execute_default_lot_cap_comes_from_profile() -> None:
    # balanced → reference lot 0.2 per order, 0.4 total
    d = evaluate_permission("open", _ctx(_exec(), requested_lot=0.5))
    assert d.mode == "execute"
    assert d.adjusted_lot == 0.2
    zero_cap = _exec(max_lot_per_order=0.0)
    total_only = evaluate_permission("open", _ctx(zero_cap, requested_lot=5.0))
    assert total_only.adjusted_lot == 0.4
    uncapped = _exec(max_lot_per_order=0.0, max_total_lots=0.0)
    assert evaluate_permission("open", _ctx(uncapped, requested_lot=5.0)).adjusted_lot is None


def test_total_lots_capacity() -> None:
    perms = _exec(max_lot_per_order=1.0, max_total_lots=0.5)
    capped = evaluate_permission("open", _ctx(perms, requested_lot=0.4, open_lots=0.3))
    assert capped.mode == "execute"
    assert capped.reason_key == REASON_LOT_CAPPED
    assert capped.adjusted_lot == 0.2
    full = evaluate_permission("open", _ctx(perms, requested_lot=0.1, open_lots=0.5))
    assert full.mode == "propose"
    assert full.downgrade_reason_key == REASON_TOTAL_LOTS
    fits = evaluate_permission("open", _ctx(perms, requested_lot=0.2, open_lots=0.3))
    assert fits.mode == "execute"
    assert fits.adjusted_lot is None
    no_cap = _exec(max_lot_per_order=1.0, max_total_lots=0.0)
    assert evaluate_permission("open", _ctx(no_cap, requested_lot=0.9, open_lots=9)).mode == "execute"


def test_lot_rules_do_not_apply_to_management_actions() -> None:
    perms = _exec(can_close_all=True, max_lot_per_order=0.01, max_lot_hard=True)
    d = evaluate_permission("close_all", _ctx(perms, requested_lot=5.0, open_lots=9.0))
    assert d.mode == "execute"
    assert d.adjusted_lot is None


# -- level 2 auto-downgrades --------------------------------------------------


def test_kill_switch_and_paused_never_execute() -> None:
    k = evaluate_permission("open", _ctx(_exec(), kill_switch=True))
    assert k.mode == "propose"
    assert k.downgrade_reason_key == REASON_KILL_SWITCH
    p = evaluate_permission("partial_close", _ctx(_exec(), paused=True))
    assert p.mode == "propose"
    assert p.downgrade_reason_key == REASON_PAUSED


def test_scope_not_granted_downgrades() -> None:
    d = evaluate_permission("close_all", _ctx(_exec()))
    assert d.mode == "propose"
    assert d.downgrade_reason_key == REASON_SCOPE_NOT_GRANTED
    w = evaluate_permission("widen_stop", _ctx(_exec()))
    assert w.downgrade_reason_key == REASON_SCOPE_NOT_GRANTED
    allowed = evaluate_permission("widen_stop", _ctx(_exec(allow_widen_stop=True)))
    assert allowed.mode == "execute"


def test_expired_grant_downgrades() -> None:
    perms = _exec(expires_at=(LONDON_NY_MS // 1000) - 1)
    d = evaluate_permission("open", _ctx(perms))
    assert d.mode == "propose"
    assert d.downgrade_reason_key == REASON_EXPIRED
    live = _exec(expires_at=(LONDON_NY_MS // 1000) + 60)
    assert evaluate_permission("open", _ctx(live)).mode == "execute"


def test_grace_period_downgrades() -> None:
    fresh = _exec(granted_at=(LONDON_NY_MS // 1000) - 3_600, grace_hours=24)
    d = evaluate_permission("open", _ctx(fresh))
    assert d.mode == "propose"
    assert d.downgrade_reason_key == REASON_GRACE
    no_grace = _exec(granted_at=(LONDON_NY_MS // 1000) - 3_600, grace_hours=0)
    assert evaluate_permission("open", _ctx(no_grace)).mode == "execute"


def test_daily_loss_ceiling_downgrades_all_actions() -> None:
    # balanced: daily_drawdown 3% → auto ceiling 1.5%
    hit = evaluate_permission("open", _ctx(_exec(), daily_loss_pct=1.5))
    assert hit.mode == "propose"
    assert hit.downgrade_reason_key == REASON_DAILY_LOSS
    mgmt = evaluate_permission("partial_close", _ctx(_exec(), daily_loss_pct=2.0))
    assert mgmt.downgrade_reason_key == REASON_DAILY_LOSS
    under = evaluate_permission("open", _ctx(_exec(), daily_loss_pct=1.49))
    assert under.mode == "execute"
    explicit = _exec(auto_daily_loss_pct=0.5)
    assert evaluate_permission("open", _ctx(explicit, daily_loss_pct=0.6)).mode == "propose"
    disabled = _exec(auto_daily_loss_pct=0.0)
    assert evaluate_permission("open", _ctx(disabled, daily_loss_pct=50)).mode == "execute"


def test_outside_session_downgrades_only_risk_increasing_actions() -> None:
    asia = evaluate_permission("open", _ctx(_exec(), now_ms=ASIA_MS))
    assert asia.mode == "propose"
    assert asia.downgrade_reason_key == REASON_OUTSIDE_SESSION
    dead = evaluate_permission("open", _ctx(_exec(), now_ms=DEAD_MS))
    assert dead.downgrade_reason_key == REASON_OUTSIDE_SESSION
    close = evaluate_permission("partial_close", _ctx(_exec(), now_ms=DEAD_MS))
    assert close.mode == "execute"
    modify = evaluate_permission("modify_sl_tp", _ctx(_exec(), now_ms=DEAD_MS))
    assert modify.mode == "execute"
    asia_ok = evaluate_permission("open", _ctx(_exec(sessions=["asia"]), now_ms=ASIA_MS))
    assert asia_ok.mode == "execute"
    any_time = evaluate_permission("open", _ctx(_exec(sessions=[]), now_ms=DEAD_MS))
    assert any_time.mode == "execute"


def test_news_lock_downgrades_open_but_not_close() -> None:
    d = evaluate_permission("open", _ctx(_exec(), news_window_active=True))
    assert d.mode == "propose"
    assert d.downgrade_reason_key == REASON_NEWS_LOCK
    c = evaluate_permission("partial_close", _ctx(_exec(), news_window_active=True))
    assert c.mode == "execute"
    unlocked = evaluate_permission("open", _ctx(_exec(news_lock=False), news_window_active=True))
    assert unlocked.mode == "execute"


def test_downgrade_precedence_kill_switch_first() -> None:
    perms = _exec(expires_at=1, granted_at=(LONDON_NY_MS // 1000))
    d = evaluate_permission("close_all", _ctx(perms, kill_switch=True, now_ms=DEAD_MS))
    assert d.downgrade_reason_key == REASON_KILL_SWITCH


def test_default_risk_params_when_none_given() -> None:
    ctx = PermissionContext(
        permissions=_exec(), now_ms=LONDON_NY_MS, requested_lot=0.5, paper_mode=False
    )
    d = evaluate_permission("open", ctx)
    assert d.mode == "execute"
    assert d.adjusted_lot == 0.2
