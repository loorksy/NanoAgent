"""Process-local risk / cooldown / toggle state for deterministic gates."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from nanobot.config.paths import get_data_dir
from nanobot.trading.policy import live

DEFAULT_TOGGLES: dict[str, bool] = {
    "news_shield": True,
    "early_exit": True,
    "spread_guard": True,
    "cooldown_lock": True,
    "drawdown_breaker": True,
    "rr_filter": True,
    "max_positions": True,
    "session_lock": True,
    "bad_tick": True,
    "stale_quote": True,
    "holiday_lock": True,
}


@dataclass
class RiskState:
    consecutive_losses: int = 0
    cooldown_until_ms: int = 0
    cooldown_reason: str = ""
    daily_pnl_pct: float = 0.0
    daily_date: str = ""
    open_positions: int = 0
    open_buy_losing: bool = False
    open_sell_losing: bool = False
    last_quote_ms: int = 0
    last_mid: float = 0.0
    last_spread_points: float = 0.0
    spread_ok_since_ms: int = 0
    emergency_lock: bool = False
    holiday: bool = False
    news_day: bool = False
    atr_baseline: float = 0.0
    feature_toggles: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_TOGGLES))
    closed_tickets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["feature_toggles"] = dict(self.feature_toggles)
        return data


class RiskStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._path = path or (get_data_dir() / "trading" / "risk_state.json")
        self._state = RiskState()
        self._load()

    def snapshot(self) -> RiskState:
        with self._lock:
            return RiskState(**self._state.to_dict())

    def update(self, **changes: Any) -> RiskState:
        with self._lock:
            for key, value in changes.items():
                if key == "feature_toggles" and isinstance(value, dict):
                    merged = dict(self._state.feature_toggles)
                    merged.update({str(k): bool(v) for k, v in value.items()})
                    self._state.feature_toggles = merged
                    continue
                if not hasattr(self._state, key):
                    raise KeyError(key)
                setattr(self._state, key, value)
            self._persist()
            return RiskState(**self._state.to_dict())

    def record_loss(self, *, news_stop: bool = False, now_ms: int | None = None) -> RiskState:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        with self._lock:
            self._state.consecutive_losses += 1
            until = 0
            reason = ""
            p = live()
            if news_stop:
                until = now + p.COOLDOWN_AFTER_NEWS_STOP_MINUTES * 60_000
                reason = "news_stop"
            if self._state.consecutive_losses >= p.COOLDOWN_CONSECUTIVE_LOSSES:
                session_ms = p.COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES * 60_000
                long_ms = p.COOLDOWN_AFTER_TWO_LOSSES_MINUTES * 60_000
                extra = now + max(session_ms, long_ms)
                if extra >= until:
                    until = extra
                    reason = "two_consecutive_losses"
            if until > self._state.cooldown_until_ms:
                self._state.cooldown_until_ms = until
                self._state.cooldown_reason = reason
            self._persist()
            return RiskState(**self._state.to_dict())

    def record_win(self) -> RiskState:
        with self._lock:
            self._state.consecutive_losses = 0
            self._persist()
            return RiskState(**self._state.to_dict())

    def toggle_enabled(self, name: str) -> bool:
        snap = self.snapshot()
        return bool(snap.feature_toggles.get(name, True))

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
            toggles = dict(DEFAULT_TOGGLES)
            extra = raw.get("feature_toggles")
            if isinstance(extra, dict):
                toggles.update({str(k): bool(v) for k, v in extra.items()})
            raw = {**raw, "feature_toggles": toggles}
            known = {f.name for f in RiskState.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            kwargs = {k: v for k, v in raw.items() if k in known}
            self._state = RiskState(**kwargs)

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._state.to_dict(), indent=2),
            encoding="utf-8",
        )


_STORE: RiskStateStore | None = None


def get_risk_store() -> RiskStateStore:
    global _STORE
    if _STORE is None:
        _STORE = RiskStateStore()
    return _STORE
