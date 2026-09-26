"""Mt5Permissions model: defaults, validation, effective limits, sessions (08 §3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mokli.config.schema import TradingRiskParameters
from mokli.trading.permissions.model import (
    ACTIONS,
    DEFAULT_SESSIONS,
    SESSION_HOURS_UTC,
    Mt5Permissions,
    PermissionDecision,
    round_lot,
    session_names_at,
)
from mokli.trading.risk_profiles import apply_profile

HOUR_MS = 3_600_000


def test_defaults_match_design() -> None:
    p = Mt5Permissions()
    assert p.level == "propose"
    assert p.can_open is False
    assert p.can_modify_sl_tp is True
    assert p.allow_widen_stop is False
    assert p.can_partial_close is True
    assert p.can_close_all is False
    assert p.can_place_pending is False
    assert p.max_lot_per_order is None
    assert p.max_lot_hard is False
    assert p.max_total_lots is None
    assert p.auto_daily_loss_pct is None
    assert p.sessions == list(DEFAULT_SESSIONS) == ["london", "newyork"]
    assert p.news_lock is True
    assert p.expires_at is None
    assert p.grace_hours == 24
    assert p.granted_at == 0
    assert p.granted_by == ""


def test_camel_case_aliases_round_trip() -> None:
    p = Mt5Permissions.model_validate(
        {"level": "execute", "canOpen": True, "maxLotPerOrder": 0.1, "grantedBy": "web-1"}
    )
    assert p.can_open is True
    assert p.max_lot_per_order == 0.1
    assert p.granted_by == "web-1"
    assert Mt5Permissions.model_validate(p.model_dump(mode="json")) == p


def test_invalid_level_and_session_rejected() -> None:
    with pytest.raises(ValidationError):
        Mt5Permissions(level="god")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Mt5Permissions(sessions=["moon"])
    with pytest.raises(ValidationError):
        Mt5Permissions(max_lot_per_order=-1)
    with pytest.raises(ValidationError):
        Mt5Permissions(auto_daily_loss_pct=150)


def test_sessions_are_normalised_and_deduplicated() -> None:
    p = Mt5Permissions(sessions=[" London ", "NEWYORK", "london"])
    assert p.sessions == ["london", "newyork"]


def test_effective_limits_derive_from_risk_profile() -> None:
    params = apply_profile(TradingRiskParameters(), "balanced")
    p = Mt5Permissions()
    assert p.effective_max_lot_per_order(params) == 0.2
    assert p.effective_max_total_lots(params) == 0.4
    assert p.effective_auto_daily_loss_pct(params) == 1.5
    explicit = Mt5Permissions(max_lot_per_order=0.05, max_total_lots=0.3, auto_daily_loss_pct=0.7)
    assert explicit.effective_max_lot_per_order(params) == 0.05
    assert explicit.effective_max_total_lots(params) == 0.3
    assert explicit.effective_auto_daily_loss_pct(params) == 0.7
    derived = p.with_derived(params)
    assert derived.max_lot_per_order == 0.2
    assert derived.max_total_lots == 0.4
    assert derived.auto_daily_loss_pct == 1.5
    assert p.max_lot_per_order is None


def test_effective_limits_per_preset() -> None:
    expected = {"conservative": (0.1, 0.1, 1.0), "balanced": (0.2, 0.4, 1.5), "aggressive": (0.4, 1.2, 2.5)}
    for name, (lot, total, ceiling) in expected.items():
        params = apply_profile(TradingRiskParameters(), name)
        p = Mt5Permissions()
        assert p.effective_max_lot_per_order(params) == lot
        assert p.effective_max_total_lots(params) == total
        assert p.effective_auto_daily_loss_pct(params) == ceiling


def test_expiry_and_grace() -> None:
    p = Mt5Permissions(granted_at=1_000, grace_hours=2, expires_at=50_000)
    assert p.in_grace_period(1_000 + 2 * 3_600 - 1) is True
    assert p.in_grace_period(1_000 + 2 * 3_600) is False
    assert p.is_expired(49_999) is False
    assert p.is_expired(50_000) is True
    assert Mt5Permissions(grace_hours=0, granted_at=1_000).in_grace_period(1_001) is False
    assert Mt5Permissions(grace_hours=24, granted_at=0).in_grace_period(10) is False
    assert Mt5Permissions().is_expired(10**12) is False


def test_scope_allows_matrix() -> None:
    p = Mt5Permissions(
        can_open=True,
        can_modify_sl_tp=True,
        allow_widen_stop=False,
        can_partial_close=False,
        can_close_all=True,
        can_place_pending=False,
    )
    assert {a: p.scope_allows(a) for a in ACTIONS} == {
        "open": True,
        "modify_sl_tp": True,
        "widen_stop": False,
        "partial_close": False,
        "close_all": True,
        "place_pending": False,
    }
    assert p.model_copy(update={"allow_widen_stop": True}).scope_allows("widen_stop") is True
    assert p.model_copy(update={"can_modify_sl_tp": False, "allow_widen_stop": True}).scope_allows(
        "widen_stop"
    ) is False
    assert p.scope_allows("teleport") is False


def test_session_windows() -> None:
    assert set(SESSION_HOURS_UTC) == {"asia", "london", "newyork", "overlap"}
    base = 1_700_006_400_000  # 2023-11-15 00:00 UTC
    assert session_names_at(base + 3 * HOUR_MS) == {"asia"}
    assert session_names_at(base + 7 * HOUR_MS) == {"asia", "london"}
    assert session_names_at(base + 10 * HOUR_MS) == {"london"}
    assert session_names_at(base + 13 * HOUR_MS) == {"london", "newyork", "overlap"}
    assert session_names_at(base + 18 * HOUR_MS) == {"newyork"}
    assert session_names_at(base + 22 * HOUR_MS) == frozenset()


def test_round_lot() -> None:
    assert round_lot(0.123) == 0.12
    assert round_lot(0.017) == 0.02
    assert round_lot(0.2) == 0.2
    assert round_lot(-1) == 0.0


def test_decision_to_dict_and_effective_level() -> None:
    d = PermissionDecision(mode="execute", reason_key="permission.lot_capped", action="open", level="execute", granted_by="ops", adjusted_lot=0.1, notes=("permission.paper_mode",))
    payload = d.to_dict()
    assert payload["effective_level"] == "execute"
    assert payload["adjusted_lot"] == 0.1
    assert payload["granted_by"] == "ops"
    assert payload["notes"] == ["permission.paper_mode"]
    assert "warnings" not in payload
    assert PermissionDecision(mode="deny", reason_key="x", action="open", level="recommend").effective_level == "recommend"
    down = PermissionDecision(mode="propose", reason_key="x", action="open", level="execute", downgrade_reason_key="permission.expired")
    assert down.effective_level == "propose"
    assert down.to_dict()["downgrade_reason_key"] == "permission.expired"
