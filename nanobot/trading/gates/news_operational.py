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
            f"Pre-news freeze — no new entries {p.PRE_NEWS_FREEZE_MINUTES:.0f}m before high-impact data",
            minutes_to_news=minutes_to,
        )
    since_s = risk.seconds_since_high_impact
    if since_s is not None and since_s < p.NEWS_VOID_SECONDS:
        return veto(
            f"First {p.FIRST_MINUTE_DEAD:.0f}s after high-impact data are a dead void",
            seconds_since_news=since_s,
        )
    since_m = risk.minutes_since_high_impact
    if since_m is not None and since_m < p.POST_NEWS_ENTRY_WAIT_MINUTES:
        return veto(
            f"Wait {p.POST_NEWS_ENTRY_WAIT_MINUTES:.0f}m after high-impact data before new entries",
            minutes_since_news=since_m,
        )
    live_px = risk.current_mid
    if (
        minutes_to is not None
        and minutes_to <= p.PRE_NEWS_FREEZE_MINUTES
        and live_px is not None
        and abs(live_px - plan.entry) / GOLD_POINT <= p.FLAT_NEAR_ENTRY_POINTS
    ):
        return veto(
            f"Position is still within {p.FLAT_NEAR_ENTRY_POINTS:.0f} points of entry ahead of news — flatten",
            distance_points=abs(live_px - plan.entry) / GOLD_POINT,
        )
    return passed()
