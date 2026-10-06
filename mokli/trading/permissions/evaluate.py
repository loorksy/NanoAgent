"""Single enforcement point: ``evaluate_permission(action, ctx)`` (08 §4).

Runs *before* the execution gates, never instead of them. Returns reason keys
only; the locale catalog turns them into text.
"""

from __future__ import annotations

from dataclasses import dataclass

from mokli.config.schema import TradingRiskParameters
from mokli.trading.permissions.model import (
    ACTIONS,
    LOT_SIZED_ACTIONS,
    RISK_INCREASING_ACTIONS,
    Mt5Permissions,
    PermissionDecision,
    round_lot,
    session_names_at,
)

REASON_RECOMMEND_ONLY = "permission.level_recommend_only"
REASON_PROPOSE = "permission.level_propose"
REASON_EXECUTED = "permission.executed_within_grant"
REASON_UNKNOWN_ACTION = "permission.unknown_action"
REASON_SCOPE_NOT_GRANTED = "permission.scope_not_granted"
REASON_KILL_SWITCH = "permission.kill_switch"
REASON_PAUSED = "permission.paused"
REASON_EXPIRED = "permission.expired"
REASON_GRACE = "permission.grace_period"
REASON_OUTSIDE_SESSION = "permission.outside_session"
REASON_DAILY_LOSS = "permission.daily_loss_ceiling"
REASON_NEWS_LOCK = "permission.news_lock"
REASON_LOT_CAPPED = "permission.lot_capped"
REASON_LOT_HARD_CAP = "permission.lot_exceeds_hard_cap"
REASON_LOT_EXCEEDS = "permission.lot_exceeds_cap"
REASON_TOTAL_LOTS = "permission.total_lots_reached"
REASON_PAPER_MODE = "permission.paper_mode"


@dataclass(frozen=True)
class PermissionContext:
    """Runtime facts the decision depends on. ``daily_loss_pct`` is a positive loss figure."""

    permissions: Mt5Permissions
    now_ms: int
    risk_params: TradingRiskParameters | None = None
    kill_switch: bool = False
    paused: bool = False
    paper_mode: bool = True
    daily_loss_pct: float = 0.0
    news_window_active: bool = False
    requested_lot: float | None = None
    open_lots: float = 0.0

    @property
    def params(self) -> TradingRiskParameters:
        return self.risk_params if self.risk_params is not None else TradingRiskParameters()


def _propose(
    action: str,
    perms: Mt5Permissions,
    *,
    downgrade: str | None = None,
    notes: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> PermissionDecision:
    return PermissionDecision(
        mode="propose",
        reason_key=REASON_PROPOSE,
        action=action,
        level=perms.level,
        granted_by=perms.granted_by,
        downgrade_reason_key=downgrade,
        notes=notes,
        warnings=warnings,
    )


def _deny(action: str, perms: Mt5Permissions, key: str) -> PermissionDecision:
    return PermissionDecision(
        mode="deny",
        reason_key=key,
        action=action,
        level=perms.level,
        granted_by=perms.granted_by,
    )


def _lot_warnings(action: str, ctx: PermissionContext) -> tuple[str, ...]:
    if action not in LOT_SIZED_ACTIONS or ctx.requested_lot is None:
        return ()
    cap = ctx.permissions.effective_max_lot_per_order(ctx.params)
    if cap > 0 and ctx.requested_lot > cap + 1e-9:
        return (REASON_LOT_EXCEEDS,)
    return ()


def _first_downgrade(action: str, ctx: PermissionContext) -> str | None:
    perms = ctx.permissions
    now_s = ctx.now_ms / 1000
    if ctx.kill_switch:
        return REASON_KILL_SWITCH
    if ctx.paused:
        return REASON_PAUSED
    if not perms.scope_allows(action):
        return REASON_SCOPE_NOT_GRANTED
    if perms.is_expired(now_s):
        return REASON_EXPIRED
    if perms.in_grace_period(now_s):
        return REASON_GRACE
    ceiling = perms.effective_auto_daily_loss_pct(ctx.params)
    if ceiling > 0 and ctx.daily_loss_pct >= ceiling:
        return REASON_DAILY_LOSS
    if action in RISK_INCREASING_ACTIONS:
        if perms.sessions and not (session_names_at(ctx.now_ms) & set(perms.sessions)):
            return REASON_OUTSIDE_SESSION
        if perms.news_lock and ctx.news_window_active:
            return REASON_NEWS_LOCK
    return None


def evaluate_permission(action: str, ctx: PermissionContext) -> PermissionDecision:
    """Decide deny / propose / execute for ``action`` under the granted permissions."""
    perms = ctx.permissions
    if action not in ACTIONS:
        return _deny(action, perms, REASON_UNKNOWN_ACTION)
    if perms.level == "recommend":
        return _deny(action, perms, REASON_RECOMMEND_ONLY)

    notes: tuple[str, ...] = (REASON_PAPER_MODE,) if ctx.paper_mode else ()
    if perms.level == "propose":
        return _propose(action, perms, notes=notes, warnings=_lot_warnings(action, ctx))

    downgrade = _first_downgrade(action, ctx)
    if downgrade is not None:
        return _propose(
            action, perms, downgrade=downgrade, notes=notes, warnings=_lot_warnings(action, ctx)
        )
    # Paper mode is a simulation. A granted execute level must not become a live
    # broker order while it is on; the operator confirms a proposal instead.
    if ctx.paper_mode:
        return _propose(
            action,
            perms,
            downgrade=REASON_PAPER_MODE,
            notes=notes,
            warnings=_lot_warnings(action, ctx),
        )

    adjusted: float | None = None
    reason = REASON_EXECUTED
    if action in LOT_SIZED_ACTIONS and ctx.requested_lot is not None:
        lot = float(ctx.requested_lot)
        cap = perms.effective_max_lot_per_order(ctx.params)
        if cap > 0 and lot > cap + 1e-9:
            if perms.max_lot_hard:
                return _deny(action, perms, REASON_LOT_HARD_CAP)
            lot = cap
            adjusted = round_lot(cap)
            reason = REASON_LOT_CAPPED
        total_cap = perms.effective_max_total_lots(ctx.params)
        if total_cap > 0:
            capacity = total_cap - max(0.0, ctx.open_lots)
            if capacity <= 1e-9:
                return _propose(action, perms, downgrade=REASON_TOTAL_LOTS, notes=notes)
            if lot > capacity + 1e-9:
                adjusted = round_lot(capacity)
                reason = REASON_LOT_CAPPED
                if adjusted <= 0:
                    return _propose(action, perms, downgrade=REASON_TOTAL_LOTS, notes=notes)

    return PermissionDecision(
        mode="execute",
        reason_key=reason,
        action=action,
        level=perms.level,
        granted_by=perms.granted_by,
        adjusted_lot=adjusted,
        notes=notes,
    )
