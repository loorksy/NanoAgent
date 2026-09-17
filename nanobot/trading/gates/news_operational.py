"""G17 — extra news operational locks on top of G1 (4.5, news 1/16/35/73)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import GOLD_POINT, live
from nanobot.trading.types import EntryPlan


def evaluate_news_operational(
    plan: EntryPlan,
    risk: RiskSnapshot | None,
) -> GateCheck:
    p = live()
    if risk is None:
        return passed()
    minutes_to = risk.minutes_to_high_impact
    if minutes_to is not None and minutes_to <= p.PRE_NEWS_FREEZE_MINUTES:
        return veto(
            "gate.news.pre_freeze",
            minutes_to_news=minutes_to,
            freeze_minutes=p.PRE_NEWS_FREEZE_MINUTES,
        )
    since_s = risk.seconds_since_high_impact
    if since_s is not None and since_s < p.NEWS_VOID_SECONDS:
        return veto(
            "gate.news.void",
            seconds_since_news=since_s,
            void_seconds=p.FIRST_MINUTE_DEAD,
        )
    since_m = risk.minutes_since_high_impact
    if since_m is not None and since_m < p.POST_NEWS_ENTRY_WAIT_MINUTES:
        return veto(
            "gate.news.post_wait",
            minutes_since_news=since_m,
            wait_minutes=p.POST_NEWS_ENTRY_WAIT_MINUTES,
        )
    live_px = risk.current_mid
    if (
        minutes_to is not None
        and minutes_to <= p.PRE_NEWS_FREEZE_MINUTES
        and live_px is not None
        and abs(live_px - plan.entry) / GOLD_POINT <= p.FLAT_NEAR_ENTRY_POINTS
    ):
        return veto(
            "gate.news.flat_near_entry",
            distance_points=abs(live_px - plan.entry) / GOLD_POINT,
            limit_points=p.FLAT_NEAR_ENTRY_POINTS,
        )
    return passed()
