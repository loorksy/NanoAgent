"""Per-strategy circuit breaker (R5). Three losses open safe mode."""

from __future__ import annotations

import threading


class StrategyCircuit:
    def __init__(self, trip_after: int = 3) -> None:
        self.trip_after = trip_after
        self._losses: dict[str, int] = {}
        self._lock = threading.Lock()

    def note_result(self, strategy: str, *, won: bool) -> dict[str, object]:
        with self._lock:
            if won:
                self._losses[strategy] = 0
            else:
                self._losses[strategy] = self._losses.get(strategy, 0) + 1
            losses = self._losses[strategy]
        return self._row(strategy, losses)

    def allows(self, strategy: str) -> bool:
        with self._lock:
            return self._losses.get(strategy, 0) < self.trip_after

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            names = sorted(self._losses)
            return [self._row(name, self._losses[name]) for name in names]

    def _row(self, strategy: str, losses: int) -> dict[str, object]:
        safe = losses >= self.trip_after
        return {
            "strategy": strategy,
            "losses": losses,
            "safe_mode": safe,
            "notice_key": "circuit.safe_mode" if safe else "",
        }


_CIRCUIT = StrategyCircuit()


def get_circuit() -> StrategyCircuit:
    return _CIRCUIT


def reset_circuit_for_tests() -> None:
    global _CIRCUIT
    _CIRCUIT = StrategyCircuit()
