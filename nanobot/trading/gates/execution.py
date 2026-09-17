"""Run G8-G20 plus execution-only checks. Used by recommendation chain and MT5 confirm."""

from __future__ import annotations

from nanobot.trading.gates.adr_gap import evaluate_adr_chase, evaluate_gap_chase
from nanobot.trading.gates.bad_tick import evaluate_bad_tick
from nanobot.trading.gates.check import GateCheck, disabled_by_operator, veto
from nanobot.trading.gates.cooldown_lock import evaluate_cooldown_lock
from nanobot.trading.gates.drawdown_breaker import evaluate_drawdown_breaker
from nanobot.trading.gates.margin_guard import evaluate_margin_guard
from nanobot.trading.gates.max_positions import evaluate_max_positions, evaluate_no_martingale
from nanobot.trading.gates.news_candle import evaluate_news_candle_shield
from nanobot.trading.gates.news_operational import evaluate_news_operational
from nanobot.trading.gates.pending_ttl import evaluate_pending_ttl
from nanobot.trading.gates.position_sizing import evaluate_position_sizing
from nanobot.trading.gates.proposal_bracket import evaluate_confirm_slippage, evaluate_proposal_ttl
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.gates.rr_filter import evaluate_rr_filter
from nanobot.trading.gates.session_lock import evaluate_session_lock
from nanobot.trading.gates.slippage_guard import evaluate_slippage_guard
from nanobot.trading.gates.spread_guard import evaluate_spread_guard
from nanobot.trading.gates.stale_quote import evaluate_stale_quote
from nanobot.trading.gates.time_stop import evaluate_time_stop
from nanobot.trading.gates.trade_management import stop_would_widen
from nanobot.trading.risk_state import EXEC_CHECK_TOGGLE
from nanobot.trading.types import EntryPlan

# Names that still block even if the operator disabled a related risk toggle.
_ALWAYS_ON = frozenset({
    "hitl",
    "proposal_ttl",
    "confirm_slippage",
    "no_widen",
    "stale_quote",
    "bad_tick",
    "margin",
    "slippage",
    "sizing",
    "martingale",
})


def _apply_toggle(name: str, check: GateCheck, risk: RiskSnapshot) -> GateCheck:
    if name in _ALWAYS_ON:
        return check
    toggle = EXEC_CHECK_TOGGLE.get(name)
    if not toggle:
        return check
    if risk.toggle(toggle):
        return check
    return disabled_by_operator(toggle)


def collect_execution_checks(
    plan: EntryPlan,
    risk: RiskSnapshot,
    *,
    now_ms: int,
    live_price: float | None = None,
    proposal_created_ms: int | None = None,
    proposed_price: float | None = None,
    adding_to_loser: bool = False,
    session_range: float | None = None,
    adr: float | None = None,
    gap_points: float | None = None,
    candle_range: float | None = None,
    operator_confirmed: bool = False,
    position_open_ms: int | None = None,
    favorable_progress: bool = False,
    current_stop: float | None = None,
    requested_stop: float | None = None,
) -> list[tuple[str, GateCheck]]:
    raw: list[tuple[str, GateCheck]] = [
        ("rr", evaluate_rr_filter(plan, live_entry=live_price)),
        ("spread", evaluate_spread_guard(risk)),
        ("cooldown", evaluate_cooldown_lock(risk, now_ms=now_ms)),
        ("max_positions", evaluate_max_positions(plan, risk)),
        ("drawdown", evaluate_drawdown_breaker(risk)),
        ("stale_quote", evaluate_stale_quote(risk)),
        ("pending", evaluate_pending_ttl(plan, risk, now_ms=now_ms, live_price=live_price)),
        ("session", evaluate_session_lock(risk, now_ms=now_ms)),
        ("bad_tick", evaluate_bad_tick(risk)),
        ("news_ops", evaluate_news_operational(plan, risk)),
        ("margin", evaluate_margin_guard(risk)),
        ("slippage", evaluate_slippage_guard(risk)),
        ("sizing", evaluate_position_sizing(plan, risk)),
        ("martingale", evaluate_no_martingale(adding_to_loser=adding_to_loser)),
    ]
    if session_range is not None and adr is not None:
        raw.append(("adr_chase", evaluate_adr_chase(session_range=session_range, adr=adr)))
    if gap_points is not None:
        raw.append(("gap_chase", evaluate_gap_chase(gap_points=gap_points)))
    if candle_range is not None and risk.atr:
        raw.append(
            ("news_candle", evaluate_news_candle_shield(candle_range=candle_range, atr=risk.atr))
        )
    if proposal_created_ms is not None:
        raw.append(("proposal_ttl", evaluate_proposal_ttl(created_ms=proposal_created_ms, now_ms=now_ms)))
    if proposed_price is not None and live_price is not None:
        raw.append(
            (
                "confirm_slippage",
                evaluate_confirm_slippage(proposed_price=proposed_price, live_price=live_price),
            )
        )
    if position_open_ms is not None:
        raw.append(
            (
                "time_stop",
                evaluate_time_stop(
                    open_ms=position_open_ms,
                    now_ms=now_ms,
                    favorable_progress=favorable_progress,
                ),
            )
        )
    if current_stop is not None and requested_stop is not None:
        if stop_would_widen(plan, current_stop=current_stop, requested_stop=requested_stop):
            raw.append(
                (
                    "no_widen",
                    veto(
                        "gate.no_widen",
                        current_stop=current_stop,
                        requested_stop=requested_stop,
                    ),
                )
            )
    if not operator_confirmed:
        raw.append(
            (
                "hitl",
                veto("gate.hitl_required", operator_confirmed=False),
            )
        )
    return [(name, _apply_toggle(name, check, risk)) for name, check in raw]


def first_blocker(checks: list[tuple[str, GateCheck]]) -> tuple[str, GateCheck] | None:
    for name, check in checks:
        if check.status == "veto":
            return name, check
        if check.status == "unavailable" and name in {
            "rr",
            "cooldown",
            "max_positions",
            "drawdown",
            "session",
            "news_ops",
            "hitl",
            "proposal_ttl",
            "time_stop",
            "no_widen",
        }:
            return name, check
    return None
