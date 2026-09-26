"""Trade-management decisions for open gold positions (T-4.2 .. T-4.6, T-8.1).

The planner is pure. ``run_management_cycle`` reads the broker and applies a
change only when the MT5 grant is ``execute`` for that action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, cast

from nanobot.trading.gates.trade_management import (
    partial_close_fraction,
    trailing_stop,
)
from nanobot.trading.geometry.detectors import momentum_is_weak
from nanobot.trading.policy import live
from nanobot.trading.types import Candle, EntryPlan

ActionKind = Literal["trail", "breakeven", "partial", "secure", "exit"]


@dataclass
class ManagedPosition:
    ticket: str
    direction: Literal["buy", "sell"]
    entry: float
    stop: float
    lot: float
    targets: list[float] = field(default_factory=list)
    closed_fraction: float = 0.0


@dataclass(frozen=True)
class ManagementAction:
    kind: ActionKind
    ticket: str
    reason_key: str
    stop: float | None = None
    volume: float | None = None
    apply: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ticket": self.ticket,
            "reason_key": self.reason_key,
            "stop": self.stop,
            "volume": self.volume,
            "apply": self.apply,
        }


def _tighter(direction: str, current: float, candidate: float) -> float | None:
    if direction == "buy" and candidate > current + 1e-9:
        return candidate
    if direction == "sell" and candidate < current - 1e-9:
        return candidate
    return None


def _plan(position: ManagedPosition) -> EntryPlan:
    return EntryPlan(
        direction=position.direction,
        entry_type="market",
        entry=position.entry,
        stop_loss=position.stop,
        targets=list(position.targets),
    )


def plan_position_actions(
    position: ManagedPosition,
    *,
    live_px: float,
    atr: float,
    minutes_to_news: float | None = None,
    candles: list[Candle] | None = None,
    swing_stop: float | None = None,
    can_modify: bool = False,
    can_partial: bool = False,
    can_close: bool = False,
    news_shield: bool = True,
    early_exit: bool = True,
) -> list[ManagementAction]:
    """Return the next management steps. ``apply`` is true only when the grant allows it."""
    actions: list[ManagementAction] = []
    plan = _plan(position)
    policy = live()

    if (
        news_shield
        and minutes_to_news is not None
        and minutes_to_news <= policy.NEWS_SHIELD_MINUTES
        and position.stop != position.entry
    ):
        secured = _tighter(position.direction, position.stop, position.entry)
        if secured is not None:
            actions.append(
                ManagementAction(
                    kind="secure",
                    ticket=position.ticket,
                    reason_key="management.news_shield",
                    stop=secured,
                    apply=can_modify,
                )
            )

    hit_tp1 = bool(position.targets) and (
        (position.direction == "buy" and live_px >= position.targets[0])
        or (position.direction == "sell" and live_px <= position.targets[0])
    )
    if hit_tp1:
        moved = _tighter(position.direction, position.stop, position.entry)
        if moved is not None:
            actions.append(
                ManagementAction(
                    kind="breakeven",
                    ticket=position.ticket,
                    reason_key="management.breakeven_after_tp1",
                    stop=moved,
                    apply=can_modify,
                )
            )

    if atr > 0:
        trail = trailing_stop(plan, live_px, atr)
        if swing_stop is not None:
            if position.direction == "buy":
                trail = max(trail, swing_stop)
            else:
                trail = min(trail, swing_stop)
        tightened = _tighter(position.direction, position.stop, trail)
        if tightened is not None:
            actions.append(
                ManagementAction(
                    kind="trail",
                    ticket=position.ticket,
                    reason_key="management.trail",
                    stop=tightened,
                    apply=can_modify,
                )
            )

    fraction = partial_close_fraction(plan, live_px)
    remaining = max(0.0, fraction - position.closed_fraction)
    volume = round(position.lot * remaining, 2)
    if volume >= 0.01:
        actions.append(
            ManagementAction(
                kind="partial",
                ticket=position.ticket,
                reason_key="management.partial",
                volume=volume,
                apply=can_partial,
            )
        )

    if early_exit and candles and momentum_is_weak(candles, direction=position.direction):
        actions.append(
            ManagementAction(
                kind="exit",
                ticket=position.ticket,
                reason_key="management.momentum_weak",
                apply=can_close,
            )
        )
    return actions


def _row_float(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        raw = row.get(key)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return float(raw)
    return 0.0


def position_from_row(row: dict[str, Any]) -> ManagedPosition | None:
    ticket = row.get("id") or row.get("positionId") or row.get("ticket")
    if ticket is None:
        return None
    side_raw = str(row.get("type") or row.get("side") or "").lower()
    if "buy" in side_raw:
        direction: Literal["buy", "sell"] = "buy"
    elif "sell" in side_raw:
        direction = "sell"
    else:
        return None
    targets_raw = row.get("targets")
    targets: list[float] = []
    if isinstance(targets_raw, list):
        for item in cast(list[object], targets_raw):
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                targets.append(float(item))
    take_profit = _row_float(row, "takeProfit", "take_profit")
    if not targets and take_profit:
        targets = [take_profit]
    return ManagedPosition(
        ticket=str(ticket),
        direction=direction,
        entry=_row_float(row, "openPrice", "entry", "price"),
        stop=_row_float(row, "stopLoss", "stop"),
        lot=_row_float(row, "volume", "lot"),
        targets=targets,
        closed_fraction=float(row.get("closed_fraction") or 0.0),
    )


def _quote_mid(quote: dict[str, Any]) -> float | None:
    body: object = quote.get("quote", quote)
    if not isinstance(body, dict):
        return None
    mapping = cast(dict[str, object], body)
    bid = mapping.get("bid")
    ask = mapping.get("ask")
    if isinstance(bid, bool) or isinstance(ask, bool):
        return None
    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)):
        return (float(bid) + float(ask)) / 2
    return None


async def run_management_cycle(
    *,
    live_px: float | None = None,
    atr: float = 0.0,
    minutes_to_news: float | None = None,
    candles: list[Candle] | None = None,
) -> dict[str, Any]:
    """Read open positions and optionally apply granted management actions."""
    from nanobot.trading.mt5_metaapi import get_transport
    from nanobot.trading.permissions.store import get_permission_store

    perms = get_permission_store().load()
    execute = perms.level == "execute"
    from nanobot.trading.risk_state import get_risk_store

    toggles = get_risk_store()
    news_shield = toggles.toggle_enabled("news_shield")
    early_exit = toggles.toggle_enabled("early_exit")
    transport = get_transport()
    rows = await transport.open_positions()
    quote_px = live_px if live_px is not None else _quote_mid(await transport.quote("XAUUSD"))
    actions: list[ManagementAction] = []
    applied: list[dict[str, Any]] = []
    if quote_px is None:
        return {"ok": False, "reason_key": "management.no_quote", "actions": [], "applied": []}
    for row in rows:
        position = position_from_row(row)
        if position is None or position.lot <= 0:
            continue
        planned = plan_position_actions(
            position,
            live_px=quote_px,
            atr=atr,
            minutes_to_news=minutes_to_news,
            candles=candles,
            can_modify=execute and perms.can_modify_sl_tp,
            can_partial=execute and perms.can_partial_close,
            can_close=execute and perms.can_close_all,
            news_shield=news_shield,
            early_exit=early_exit,
        )
        actions.extend(planned)
        for action in planned:
            if not action.apply:
                continue
            if action.kind in {"trail", "breakeven", "secure"} and action.stop is not None:
                result = await transport.modify_position(
                    {"position_id": action.ticket, "stop": action.stop, "take_profit": None}
                )
                applied.append({"action": action.to_dict(), "result": result})
            elif action.kind == "partial" and action.volume is not None:
                result = await transport.close_partial(
                    {"position_id": action.ticket, "volume": action.volume}
                )
                applied.append({"action": action.to_dict(), "result": result})
            elif action.kind == "exit":
                result = await transport.close_position({"position_id": action.ticket})
                applied.append({"action": action.to_dict(), "result": result})
    return {
        "ok": True,
        "positions": len(rows),
        "actions": [action.to_dict() for action in actions],
        "applied": applied,
    }
