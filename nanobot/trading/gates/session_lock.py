"""G15 — session, rollover, midnight-spread, holiday, and daily-close locks."""

from __future__ import annotations

from datetime import UTC, datetime

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live

# Recurring US / bank holidays used for playbook 197 (no paid calendar).
# Month-day fixed observances; NFP Friday is handled via news_day on the snapshot.
FIXED_HOLIDAYS = {
    (1, 1),  # New Year
    (7, 4),  # US Independence Day (approx)
    (12, 25),  # Christmas
    (11, 24),  # Thanksgiving week placeholder (operator can set holiday=True)
}


def _in_midnight_spread_window(hour: int, minute: int) -> bool:
    p = live()
    start_h, start_m = p.MIDNIGHT_SPREAD_START_HM
    end_h, end_m = p.MIDNIGHT_SPREAD_END_HM
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m
    cur = hour * 60 + minute
    if start > end:
        return cur >= start or cur < end
    return start <= cur < end


def _in_rollover_minutes(minute: int) -> bool:
    p = live()
    return minute >= p.ROLLOVER_MINUTE_START or minute <= p.ROLLOVER_MINUTE_END


def evaluate_session_lock(risk: RiskSnapshot | None, *, now_ms: int) -> GateCheck:
    p = live()
    dt = datetime.fromtimestamp(now_ms / 1000, tz=UTC)
    if (risk is not None and risk.holiday) or (dt.month, dt.day) in FIXED_HOLIDAYS:
        return veto("Holiday lock — no new gold orders", holiday=True)
    if _in_midnight_spread_window(dt.hour, dt.minute):
        return veto(
            "Midnight spread trap window — no new orders or tight stops",
            hour=dt.hour,
            minute=dt.minute,
        )
    if _in_rollover_minutes(dt.minute):
        news_context = bool(
            risk is not None
            and (
                risk.news_day
                or (
                    risk.minutes_to_high_impact is not None
                    and risk.minutes_to_high_impact <= p.ROLLOVER_NEWS_MINUTES
                )
            )
        )
        if news_context:
            return veto(
                "Rollover minute window during news — no new orders",
                minute=dt.minute,
            )
    minutes_to_close = (p.DAILY_CLOSE_HOUR_UTC * 60) - (dt.hour * 60 + dt.minute)
    if 0 <= minutes_to_close <= p.DAILY_CLOSE_LOCK_MINUTES:
        return veto(
            f"No new positions in the last {p.DAILY_CLOSE_LOCK_MINUTES:.0f}m before daily close",
            minutes_to_close=minutes_to_close,
        )
    return passed(hour=dt.hour, minute=dt.minute)
