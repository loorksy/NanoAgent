"""Recommendation outcome finite state machine — Phase M."""

from __future__ import annotations

from typing import Literal

OutcomeStatus = Literal[
    "valid_now",
    "awaiting_activation",
    "waiting",
    "in_trade",
    "tp1",
    "invalidated",
    "expired",
]

LIVE_STATES: frozenset[str] = frozenset(
    {"valid_now", "awaiting_activation", "waiting", "in_trade"}
)
CLOSED_STATES: frozenset[str] = frozenset({"tp1", "invalidated", "expired"})
TERMINAL_STATES: frozenset[str] = CLOSED_STATES
LIVE_OUTCOME_STATUSES = LIVE_STATES
CLOSED_OUTCOME_STATUSES = CLOSED_STATES

_ALLOWED: dict[str, frozenset[str]] = {
    "valid_now": frozenset(
        {"awaiting_activation", "waiting", "in_trade", "invalidated", "expired", "tp1"}
    ),
    "awaiting_activation": frozenset(
        {"waiting", "in_trade", "invalidated", "expired", "tp1", "valid_now"}
    ),
    "waiting": frozenset(
        {"in_trade", "invalidated", "expired", "tp1", "valid_now", "awaiting_activation"}
    ),
    "in_trade": frozenset({"waiting", "tp1", "invalidated", "expired"}),
    "tp1": frozenset(),
    "invalidated": frozenset(),
    "expired": frozenset(),
}


def normalize_outcome_status(status: str | None) -> str:
    value = (status or "valid_now").strip()
    if value in _ALLOWED:
        return value
    return "valid_now"


def can_transition(previous: str, current: str) -> bool:
    """Return True when ``current`` is a legal FSM transition from ``previous``."""
    prev = normalize_outcome_status(previous)
    cur = normalize_outcome_status(current)
    if prev == cur:
        return True
    if prev in TERMINAL_STATES:
        return False
    return cur in _ALLOWED.get(prev, frozenset())


def is_live_status(status: str) -> bool:
    return normalize_outcome_status(status) in LIVE_STATES


def is_closed_status(status: str) -> bool:
    return normalize_outcome_status(status) in CLOSED_STATES
