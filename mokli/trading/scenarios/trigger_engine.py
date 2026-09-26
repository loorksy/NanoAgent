"""Activate the first of two price scenarios and cancel the other (T-8.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["buy", "sell"]


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    direction: Direction
    trigger: float
    invalidation: float


def _hit(spec: ScenarioSpec, price: float) -> bool:
    if spec.direction == "buy":
        return price >= spec.trigger
    return price <= spec.trigger


def _invalidated(spec: ScenarioSpec, price: float) -> bool:
    if spec.direction == "buy":
        return price <= spec.invalidation
    return price >= spec.invalidation


class ScenarioWatch:
    """Tick watcher. The first scenario whose trigger prints wins; the other is cancelled."""

    def __init__(self, primary: ScenarioSpec, alternate: ScenarioSpec) -> None:
        self.primary = primary
        self.alternate = alternate
        self.winner: ScenarioSpec | None = None
        self.cancelled_id: str | None = None
        self.invalidated_id: str | None = None

    def on_price(self, price: float) -> ScenarioSpec | None:
        if self.winner is not None or self.invalidated_id is not None:
            return self.winner
        for spec, other in (
            (self.primary, self.alternate),
            (self.alternate, self.primary),
        ):
            if _invalidated(spec, price) and _invalidated(other, price):
                self.invalidated_id = spec.id
                return None
            if _hit(spec, price):
                self.winner = spec
                self.cancelled_id = other.id
                return spec
        return None

    def to_dict(self) -> dict[str, object]:
        winner = self.winner
        return {
            "primary": self.primary.id,
            "alternate": self.alternate.id,
            "active": None if winner is None else winner.id,
            "cancelled": self.cancelled_id,
            "invalidated": self.invalidated_id,
        }
