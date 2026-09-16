"""MT5 HITL execution service: propose never sends; confirm runs gates then transport."""

from __future__ import annotations

import time
from typing import Any

from nanobot.trading.gates.execution import collect_execution_checks, first_blocker
from nanobot.trading.gates.position_sizing import lot_from_balance
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.mt5_metaapi import get_transport
from nanobot.trading.mt5_proposals import OrderProposal, get_proposal_store
from nanobot.trading.policy import GOLD_POINT, MAGIC_SCALP, MAGIC_SWING
from nanobot.trading.risk_state import get_risk_store
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.trading.types import EntryPlan

GOLD_SYMBOL = "XAUUSD"


def _plan_from_proposal(p: OrderProposal) -> EntryPlan:
    return EntryPlan(
        direction="buy" if p.side.lower() in {"buy", "long"} else "sell",
        entry_type=p.order_type,
        entry=p.entry,
        stop_loss=p.stop,
        targets=list(p.targets),
    )


def _risk_from_account(account: dict[str, Any], quote: dict[str, Any] | None) -> RiskSnapshot:
    stored = get_risk_store().snapshot()
    runtime = get_runtime_store().snapshot()
    info = account.get("account") if isinstance(account.get("account"), dict) else account
    bid = ask = mid = None
    if quote:
        q = quote.get("quote") if isinstance(quote.get("quote"), dict) else quote
        bid = q.get("bid") if isinstance(q, dict) else None
        ask = q.get("ask") if isinstance(q, dict) else None
        if bid is not None and ask is not None:
            mid = (float(bid) + float(ask)) / 2
    spread = None
    if bid is not None and ask is not None:
        spread = abs(float(ask) - float(bid)) / GOLD_POINT
    balance = info.get("balance") if isinstance(info, dict) else None
    equity = info.get("equity") if isinstance(info, dict) else None
    margin = info.get("marginLevel") or info.get("margin_level") if isinstance(info, dict) else None
    return RiskSnapshot(
        spread_points=spread,
        quote_age_seconds=0.0 if mid is not None else None,
        bid=None if bid is None else float(bid),
        ask=None if ask is None else float(ask),
        current_mid=mid,
        last_mid=stored.last_mid or mid,
        open_positions=int(stored.open_positions),
        open_buy_losing=stored.open_buy_losing,
        open_sell_losing=stored.open_sell_losing,
        daily_drawdown_pct=max(0.0, -float(stored.daily_pnl_pct or 0.0)),
        consecutive_losses=stored.consecutive_losses,
        cooldown_until_ms=stored.cooldown_until_ms,
        account_balance=None if balance is None else float(balance),
        account_equity=None if equity is None else float(equity),
        margin_level_pct=None if margin is None else float(margin),
        kill_switch=runtime.kill_switch,
        emergency_lock=stored.emergency_lock,
        holiday=stored.holiday,
        news_day=stored.news_day,
        feature_toggles=dict(stored.feature_toggles),
    )


async def mt5_get_account() -> dict[str, Any]:
    transport = get_transport()
    account = await transport.account_snapshot()
    quote = await transport.quote(GOLD_SYMBOL)
    positions = await transport.open_positions()
    return {"ok": True, "account": account, "quote": quote, "positions": positions}


async def mt5_propose_order(
    *,
    side: str,
    lot: float | None = None,
    entry: float,
    stop: float,
    targets: list[float],
    comment: str = "",
    order_type: str = "market",
    style: str = "swing",
) -> dict[str, Any]:
    account = await get_transport().account_snapshot()
    info = account.get("account") if isinstance(account.get("account"), dict) else account
    balance = float((info or {}).get("balance") or 0) if isinstance(info, dict) else 0.0
    sized = lot
    if sized is None and balance > 0:
        sized = lot_from_balance(balance, entry, stop)
    if sized is None:
        sized = 0.0
    magic = MAGIC_SWING if style != "scalp" else MAGIC_SCALP
    note = comment or "MANUAL_CONFIRM"
    proposal = get_proposal_store().create(
        symbol=GOLD_SYMBOL,
        side=side.lower(),
        lot=float(sized),
        entry=entry,
        stop=stop,
        targets=targets,
        comment=note,
        order_type=order_type,
        extra={"magic": magic},
    )
    return {
        "ok": True,
        "status": "proposed",
        "executed": False,
        "proposal": proposal.to_public(),
        "operator_must_confirm": True,
        "display": {
            "symbol": GOLD_SYMBOL,
            "side": proposal.side,
            "lot": proposal.lot,
            "entry": proposal.entry,
            "stop": proposal.stop,
            "targets": proposal.targets,
        },
    }


async def mt5_confirm_order(*, proposal_id: str, confirm: bool = False) -> dict[str, Any]:
    store = get_proposal_store()
    proposal = store.get(proposal_id)
    if proposal is None:
        return {"ok": False, "error": "Unknown proposal id"}
    now = int(time.time() * 1000)
    transport = get_transport()
    account = await transport.account_snapshot()
    quote = await transport.quote(GOLD_SYMBOL)
    risk = _risk_from_account(account, quote)
    live = risk.current_mid or proposal.entry
    checks = collect_execution_checks(
        _plan_from_proposal(proposal),
        risk,
        now_ms=now,
        live_price=live,
        proposal_created_ms=proposal.created_ms,
        proposed_price=proposal.entry,
        operator_confirmed=bool(confirm),
    )
    blocker = first_blocker(checks)
    if blocker is not None:
        name, check = blocker
        return {
            "ok": False,
            "executed": False,
            "blocked_by": name,
            "reason": check.reason,
            "proposal": proposal.to_public(),
        }
    store.mark_confirmed(proposal_id)
    tp = proposal.targets[0] if proposal.targets else None
    sent = await transport.send_market(
        {
            "symbol": proposal.symbol,
            "side": proposal.side,
            "lot": proposal.lot,
            "stop": proposal.stop,
            "take_profit": tp,
            "comment": proposal.comment,
        }
    )
    position_id = str((sent.get("result") or {}).get("positionId") or sent.get("position_id") or proposal.id)
    store.mark_executed(proposal_id, position_id)
    return {"ok": True, "executed": True, "send": sent, "proposal": proposal.to_public()}


async def mt5_modify_order(
    *,
    position_id: str,
    stop: float | None = None,
    take_profit: float | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "executed": False, "error": "Human confirmation required to modify"}
    if get_runtime_store().snapshot().kill_switch:
        return {"ok": False, "error": "Kill switch is engaged"}
    sent = await get_transport().modify_position(
        {"position_id": position_id, "stop": stop, "take_profit": take_profit}
    )
    return {"ok": True, "executed": True, "send": sent}


async def mt5_close_position(*, position_id: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "executed": False, "error": "Human confirmation required to close"}
    sent = await get_transport().close_position({"position_id": position_id})
    return {"ok": True, "executed": True, "send": sent}
