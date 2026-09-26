"""MT5 agent permission model (08 §3) and derivation from the risk profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

from pydantic import Field, field_validator

from nanobot.config.schema import TradingRiskParameters
from nanobot.config_base import Base
from nanobot.trading.risk_profiles import LOT_STEP, reference_lot

PermissionLevel = Literal["recommend", "propose", "execute"]
PermissionAction = Literal[
    "open",
    "modify_sl_tp",
    "widen_stop",
    "partial_close",
    "close_all",
    "place_pending",
]
PermissionMode = Literal["deny", "propose", "execute"]

LEVELS: Final[tuple[str, ...]] = ("recommend", "propose", "execute")
ACTIONS: Final[tuple[str, ...]] = (
    "open",
    "modify_sl_tp",
    "widen_stop",
    "partial_close",
    "close_all",
    "place_pending",
)

# Actions that add or widen exposure — subject to session, news and lot limits.
RISK_INCREASING_ACTIONS: Final[frozenset[str]] = frozenset({"open", "place_pending", "widen_stop"})
LOT_SIZED_ACTIONS: Final[frozenset[str]] = frozenset({"open", "place_pending"})

# Half-open UTC hour windows [start, end).
SESSION_HOURS_UTC: Final[dict[str, tuple[int, int]]] = {
    "asia": (0, 8),
    "london": (7, 16),
    "newyork": (12, 21),
    "overlap": (12, 16),
}
SESSION_NAMES: Final[tuple[str, ...]] = tuple(SESSION_HOURS_UTC)
DEFAULT_SESSIONS: Final[tuple[str, ...]] = ("london", "newyork")

DEFAULT_GRACE_HOURS: Final[int] = 24
DEFAULT_EXPIRY_DAYS: Final[int] = 7
AUTO_DAILY_LOSS_SHARE: Final[float] = 0.5

SECONDS_PER_HOUR: Final[int] = 3_600


class Mt5Permissions(Base):
    """Operator-granted scope for the agent on the linked MT5 account."""

    level: PermissionLevel = "propose"
    can_open: bool = False
    can_modify_sl_tp: bool = True
    allow_widen_stop: bool = False
    can_partial_close: bool = True
    can_close_all: bool = False
    can_place_pending: bool = False
    max_lot_per_order: float | None = Field(default=None, ge=0)
    max_lot_hard: bool = False
    max_total_lots: float | None = Field(default=None, ge=0)
    auto_daily_loss_pct: float | None = Field(default=None, ge=0, le=100)
    sessions: list[str] = Field(default_factory=lambda: list(DEFAULT_SESSIONS))
    news_lock: bool = True
    expires_at: int | None = Field(default=None, ge=0)
    grace_hours: int = Field(default=DEFAULT_GRACE_HOURS, ge=0)
    granted_at: int = Field(default=0, ge=0)
    granted_by: str = ""
    upgrade_requires_biometric: bool = True

    @field_validator("sessions")
    @classmethod
    def _known_sessions(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in value:
            name = str(raw).strip().lower()
            if name not in SESSION_HOURS_UTC:
                raise ValueError(f"unknown session {raw!r}")
            if name not in cleaned:
                cleaned.append(name)
        return cleaned

    # -- effective limits ---------------------------------------------------

    def effective_max_lot_per_order(self, params: TradingRiskParameters) -> float:
        """Explicit grant, else the profile's reference lot at ``risk_pct_default``. 0 = no cap."""
        if self.max_lot_per_order is not None:
            return float(self.max_lot_per_order)
        return reference_lot(params.risk_pct_default)

    def effective_max_total_lots(self, params: TradingRiskParameters) -> float:
        """Explicit grant, else ``TradingRiskParameters.max_total_lots``. 0 = no cap."""
        if self.max_total_lots is not None:
            return float(self.max_total_lots)
        return float(params.max_total_lots)

    def effective_auto_daily_loss_pct(self, params: TradingRiskParameters) -> float:
        """Explicit grant, else half the daily drawdown breaker. 0 = disabled."""
        if self.auto_daily_loss_pct is not None:
            return float(self.auto_daily_loss_pct)
        return round(float(params.daily_drawdown_pct) * AUTO_DAILY_LOSS_SHARE, 4)

    def is_expired(self, now_s: float) -> bool:
        return self.expires_at is not None and now_s >= self.expires_at

    def in_grace_period(self, now_s: float) -> bool:
        if self.grace_hours <= 0 or self.granted_at <= 0:
            return False
        return now_s < self.granted_at + self.grace_hours * SECONDS_PER_HOUR

    def scope_allows(self, action: str) -> bool:
        if action == "open":
            return self.can_open
        if action == "modify_sl_tp":
            return self.can_modify_sl_tp
        if action == "widen_stop":
            return self.can_modify_sl_tp and self.allow_widen_stop
        if action == "partial_close":
            return self.can_partial_close
        if action == "close_all":
            return self.can_close_all
        if action == "place_pending":
            return self.can_place_pending
        return False

    def with_derived(self, params: TradingRiskParameters) -> Mt5Permissions:
        """Copy with every ``None`` limit filled from the risk profile."""
        return self.model_copy(
            update={
                "max_lot_per_order": self.effective_max_lot_per_order(params),
                "max_total_lots": self.effective_max_total_lots(params),
                "auto_daily_loss_pct": self.effective_auto_daily_loss_pct(params),
            }
        )


def session_names_at(now_ms: int) -> frozenset[str]:
    """Sessions whose UTC window contains ``now_ms``."""
    hour = int((now_ms // 1000) % 86_400) // SECONDS_PER_HOUR
    return frozenset(
        name for name, (start, end) in SESSION_HOURS_UTC.items() if start <= hour < end
    )


def round_lot(value: float) -> float:
    return max(0.0, round(round(value / LOT_STEP) * LOT_STEP, 2))


@dataclass(frozen=True)
class PermissionDecision:
    """Outcome of ``evaluate_permission`` — reason keys only, no prose."""

    mode: PermissionMode
    reason_key: str
    action: str
    level: str
    granted_by: str = ""
    adjusted_lot: float | None = None
    downgrade_reason_key: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def effective_level(self) -> str:
        if self.mode == "execute":
            return "execute"
        if self.mode == "deny":
            return "recommend"
        return "propose"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode,
            "reason_key": self.reason_key,
            "action": self.action,
            "level": self.level,
            "effective_level": self.effective_level,
        }
        if self.granted_by:
            payload["granted_by"] = self.granted_by
        if self.adjusted_lot is not None:
            payload["adjusted_lot"] = self.adjusted_lot
        if self.downgrade_reason_key:
            payload["downgrade_reason_key"] = self.downgrade_reason_key
        if self.notes:
            payload["notes"] = list(self.notes)
        if self.warnings:
            payload["warnings"] = list(self.warnings)
        return payload
