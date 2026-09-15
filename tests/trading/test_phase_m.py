"""Tests for Phase M state machine, alert dedup, and observability."""

from nanobot.trading.recommendations.outcome_alerts import (
    OutcomeTransition,
    should_alert_transition,
)
from nanobot.trading.recommendations.state_machine import (
    can_transition,
    is_closed_status,
    is_live_status,
    normalize_outcome_status,
)


def test_fsm_live_to_in_trade_allowed() -> None:
    assert can_transition("waiting", "in_trade")
    assert is_live_status("in_trade")


def test_fsm_terminal_blocks_reopen() -> None:
    assert not can_transition("tp1", "in_trade")
    assert is_closed_status("invalidated")


def test_fsm_oscillation_waiting_in_trade_allowed_for_grading() -> None:
    assert can_transition("in_trade", "waiting")
    assert can_transition("waiting", "in_trade")


def test_alert_suppresses_waiting_in_trade_oscillation() -> None:
    assert not should_alert_transition(
        OutcomeTransition("r1", "in_trade", "waiting", row={})
    )
    assert not should_alert_transition(
        OutcomeTransition("r1", "waiting", "in_trade", row={})
    )


def test_alert_allows_first_in_trade_from_valid_now() -> None:
    assert should_alert_transition(
        OutcomeTransition("r1", "valid_now", "in_trade", row={})
    )


def test_alert_allows_tp1_and_invalidated() -> None:
    assert should_alert_transition(
        OutcomeTransition("r1", "in_trade", "tp1", row={})
    )
    assert should_alert_transition(
        OutcomeTransition("r1", "waiting", "invalidated", row={})
    )


def test_normalize_unknown_status_to_valid_now() -> None:
    assert normalize_outcome_status("unknown") == "valid_now"
