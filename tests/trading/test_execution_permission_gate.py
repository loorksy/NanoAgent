"""``permission`` gate sits after ``hitl`` and passes on confirm OR execute-mode (08 §4.1)."""

from __future__ import annotations

from datetime import UTC, datetime

from mokli.trading.gates.execution import (
    collect_execution_checks,
    evaluate_permission_gate,
    first_blocker,
)
from mokli.trading.gates.position_sizing import lot_from_balance
from mokli.trading.gates.risk_snapshot import RiskSnapshot
from mokli.trading.types import EntryPlan


def _noon_ms() -> int:
    return int(datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp() * 1000)


def _plan() -> EntryPlan:
    return EntryPlan(
        direction="buy",
        entry_type="market",
        entry=2650.0,
        stop_loss=2640.0,
        targets=[2680.0],
    )


def _clean_risk(plan: EntryPlan) -> RiskSnapshot:
    return RiskSnapshot(
        spread_points=20,
        quote_age_seconds=1,
        last_mid=plan.entry,
        current_mid=plan.entry,
        account_balance=10_000,
        proposed_lot=lot_from_balance(10_000, plan.entry, plan.stop_loss),
        margin_level_pct=800,
    )


def test_permission_gate_unit() -> None:
    assert evaluate_permission_gate(operator_confirmed=True, permission_mode=None).status == "pass"
    ok = evaluate_permission_gate(operator_confirmed=False, permission_mode="execute")
    assert ok.status == "pass"
    assert ok.evidence == {"operator_confirmed": False, "permission_mode": "execute"}
    for mode in (None, "propose", "deny"):
        blocked = evaluate_permission_gate(operator_confirmed=False, permission_mode=mode)
        assert blocked.status == "veto"
        assert blocked.reason_key == "gate.permission_required"
        assert blocked.reason_params["permission_mode"] == (mode or "none")


def test_permission_gate_is_present_and_ordered_after_hitl() -> None:
    plan = _plan()
    checks = collect_execution_checks(plan, RiskSnapshot(), now_ms=_noon_ms(), operator_confirmed=False)
    names = [name for name, _ in checks]
    assert "hitl" in names
    assert "permission" in names
    assert names.index("permission") == names.index("hitl") + 1
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "hitl"
    assert dict(checks)["permission"].status == "veto"


def test_hitl_stays_locked_without_confirm_even_in_execute_mode() -> None:
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        _clean_risk(plan),
        now_ms=_noon_ms(),
        operator_confirmed=False,
        permission_mode="execute",
    )
    by_name = dict(checks)
    assert by_name["permission"].status == "pass"
    assert by_name["hitl"].status == "veto"
    blocker = first_blocker(checks)
    assert blocker is not None
    assert blocker[0] == "hitl"


def test_permission_execution_counts_as_prior_confirmation() -> None:
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        _clean_risk(plan),
        now_ms=_noon_ms(),
        operator_confirmed=True,
        permission_mode="execute",
        proposal_created_ms=_noon_ms(),
        proposed_price=plan.entry,
        live_price=plan.entry,
    )
    assert "hitl" not in dict(checks)
    assert dict(checks)["permission"].status == "pass"
    assert first_blocker(checks) is None


def test_operator_confirmation_alone_still_passes_permission() -> None:
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        _clean_risk(plan),
        now_ms=_noon_ms(),
        operator_confirmed=True,
        permission_mode="propose",
    )
    assert dict(checks)["permission"].status == "pass"
    assert first_blocker(checks) is None


def test_permission_gate_cannot_be_disabled_by_operator_toggle() -> None:
    plan = _plan()
    checks = collect_execution_checks(
        plan,
        RiskSnapshot(feature_toggles={"permission": False, "hitl": False}),
        now_ms=_noon_ms(),
        operator_confirmed=False,
    )
    by_name = dict(checks)
    assert by_name["permission"].status == "veto"
    assert by_name["permission"].evidence.get("disabled_by_operator") is not True
    assert by_name["hitl"].status == "veto"
