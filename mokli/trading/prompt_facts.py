"""Trading runtime facts injected into the system prompt for every turn.

Facts are plain key/value rows rendered by the prompt composer. They tell the
model the operator's current MT5 permission level and the platform run mode so
its wording ("I recommend…" / "I propose…" / "Executed…") matches what the
execution gate will actually allow.
"""

from __future__ import annotations

from collections.abc import Mapping

from loguru import logger

from mokli.agent.tools.context import RequestContext


def _scope_summary(perms: object) -> str:
    allowed = [
        name
        for flag, name in (
            ("can_open", "open"),
            ("can_modify_sl_tp", "modify_sl_tp"),
            ("can_partial_close", "partial_close"),
            ("can_close_all", "close_all"),
            ("can_place_pending", "pending_orders"),
        )
        if getattr(perms, flag, False)
    ]
    bits = ["actions=" + (",".join(allowed) or "none")]
    max_lot = getattr(perms, "max_lot_per_order", None)
    if max_lot:
        bits.append(f"max_lot_per_order={max_lot}")
    max_total = getattr(perms, "max_total_lots", None)
    if max_total:
        bits.append(f"max_total_lots={max_total}")
    loss = getattr(perms, "auto_daily_loss_pct", None)
    if loss:
        bits.append(f"auto_daily_loss_pct={loss}")
    sessions = getattr(perms, "sessions", None)
    if sessions:
        bits.append("sessions=" + ",".join(str(x) for x in sessions))
    expires = getattr(perms, "expires_at", None)
    if expires:
        bits.append(f"expires_at_epoch={expires}")
    return "; ".join(bits)


def trading_prompt_facts(request: RequestContext) -> Mapping[str, str]:
    facts: dict[str, str] = {
        "instrument": (
            "every tradable symbol on the connected MT5 account; "
            "live bid/ask and candles come from that account"
        ),
        "market_data": "broker live prices from the operator's MT5 terminal",
    }

    try:
        from mokli.trading.permissions.store import get_permission_store

        perms = get_permission_store().load()
        facts["mt5_permission_level"] = str(perms.level)
        if perms.level == "execute":
            facts["mt5_execute_scope"] = _scope_summary(perms)
    except Exception as exc:  # the prompt must never fail because of storage
        logger.debug("permission facts unavailable: {}", exc)
        facts["mt5_permission_level"] = "recommend"

    try:
        from mokli.trading.runtime_state import get_runtime_store

        runtime = get_runtime_store().snapshot()
        facts["execution_mode"] = "paper" if runtime.paper_mode else "live"
        if runtime.kill_switch:
            facts["kill_switch"] = "active — no new orders"
        if getattr(runtime, "paused", False):
            facts["trading_paused"] = "yes"
    except Exception as exc:
        logger.debug("runtime facts unavailable: {}", exc)

    if request.channel:
        facts["channel"] = request.channel
    return facts
