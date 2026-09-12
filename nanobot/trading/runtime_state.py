"""Process-local trading runtime controls (pause, kill switch, paper mode)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from nanobot.config.paths import get_data_dir


@dataclass
class TradingRuntimeState:
    paused: bool = False
    kill_switch: bool = False
    paper_mode: bool = True

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


class TradingRuntimeStore:
    """Thread-safe runtime state persisted under ~/.nanobot/trading/."""

    def __init__(self, path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._path = path or (get_data_dir() / "trading" / "runtime_state.json")
        self._state = TradingRuntimeState()
        self._load()

    def snapshot(self) -> TradingRuntimeState:
        with self._lock:
            return TradingRuntimeState(**self._state.to_dict())

    def update(self, **changes: bool) -> TradingRuntimeState:
        with self._lock:
            for key, value in changes.items():
                if not hasattr(self._state, key):
                    raise KeyError(key)
                setattr(self._state, key, bool(value))
            self._persist()
            return TradingRuntimeState(**self._state.to_dict())

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        with self._lock:
            for key in ("paused", "kill_switch", "paper_mode"):
                if key in raw:
                    setattr(self._state, key, bool(raw[key]))

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._state.to_dict(), indent=2),
            encoding="utf-8",
        )


_STORE: TradingRuntimeStore | None = None


def get_runtime_store() -> TradingRuntimeStore:
    global _STORE
    if _STORE is None:
        _STORE = TradingRuntimeStore()
    return _STORE
