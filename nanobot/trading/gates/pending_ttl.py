"""G14 — pending order TTL, stale ideas, and half-distance chase (12, 183, 193, news 2 / 65)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live
from nanobot.trading.types import EntryPlan


def evaluate_pending_ttl(
    plan: EntryPlan,
    risk: RiskSnapshot | None,
    *,
    now_ms: int,
    live_price: float | None = None,
) -> GateCheck:
    p = live()
    created = None if risk is None else risk.pending_created_ms
    if created is not None:
        age_h = (now_ms - created) / 3_600_000
        limit = min(p.PENDING_TTL_HOURS, p.IDEA_STALE_HOURS)
        if age_h >= limit:
            return veto(
                f"Pending context expired after {age_h:.1f}h (limit {limit:.0f}h)",
                age_hours=age_h,
                limit_hours=limit,
            )
    minutes = None if risk is None else risk.minutes_to_high_impact
    if minutes is not None and minutes <= p.NEWS_SHIELD_MINUTES:
        return veto(
            f"Pending orders must be cancelled {p.NEWS_SHIELD_MINUTES:.0f}m before high-impact news",
            minutes_to_news=minutes,
        )
    price = live_price if live_price is not None else (None if risk is None else risk.current_mid)
    if price is not None and plan.targets:
        risk_dist = abs(plan.entry - plan.stop_loss)
        toward = max(abs(t - plan.entry) for t in plan.targets)
        if toward > 0:
            moved = abs(price - plan.entry)
            first = plan.targets[0]
            favorable = (first > plan.entry and price > plan.entry) or (
                first < plan.entry and price < plan.entry
            )
            if favorable and moved >= toward * p.HALF_DISTANCE_FRACTION:
                return veto(
                    "Price already ran half the distance to target — pending entry cancelled",
                    moved=moved,
                    target_distance=toward,
                    stop_distance=risk_dist,
                )
    return passed()
