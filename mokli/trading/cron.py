"""Cron hooks for gold trading monitors."""

from __future__ import annotations

import logging
from typing import cast

from mokli.cron.types import CronJob, CronPayload, CronSchedule
from mokli.trading.bots.coordinator import run_bot_cycle

logger = logging.getLogger(__name__)

GOLD_SCAN_JOB_ID = "gold_scan"
GOLD_NEWS_JOB_ID = "gold_news"
GOLD_FOLLOWUP_JOB_ID = "gold_rec_followup"
MORNING_BRIEFING_JOB_ID = "morning_briefing"
SCORECARD_JOB_ID = "scorecard"
DAILY_WRAP_JOB_ID = "daily_wrap"
TRADE_MANAGEMENT_JOB_ID = "trade_management"
TRADABILITY_JOB_ID = "tradability_calibration"
EVENT_MONITOR_JOB_ID = "event_monitor"
OPPORTUNITY_SCAN_JOB_ID = "opportunity_scan"
COT_REFRESH_JOB_ID = "cot_refresh"

TRADING_CRON_JOB_IDS = (
    GOLD_SCAN_JOB_ID,
    GOLD_NEWS_JOB_ID,
    GOLD_FOLLOWUP_JOB_ID,
    MORNING_BRIEFING_JOB_ID,
    SCORECARD_JOB_ID,
    DAILY_WRAP_JOB_ID,
    TRADE_MANAGEMENT_JOB_ID,
    TRADABILITY_JOB_ID,
    EVENT_MONITOR_JOB_ID,
    OPPORTUNITY_SCAN_JOB_ID,
    COT_REFRESH_JOB_ID,
)


def register_trading_cron_jobs(
    cron_service: object,
    timezone: str = "UTC",
    *,
    enabled: bool = False,
) -> None:
    """Register or remove background gold monitor jobs.

    When disabled (default), removes gold_scan / gold_news / gold_rec_followup so
    Telegram/WhatsApp are not spammed by fixed-interval bot scanners.
    """
    register = getattr(cron_service, "register_system_job", None)
    remove = getattr(cron_service, "remove_system_job", None)
    if remove is not None:
        for job_id in TRADING_CRON_JOB_IDS:
            remove(job_id)
    if not enabled or register is None:
        if not enabled:
            logger.info(
                "Cron: gold trading monitor jobs disabled (opt-in via gateway.tradingCron.enabled)"
            )
        return
    schedules = {
        GOLD_SCAN_JOB_ID: CronSchedule(kind="every", every_ms=30 * 60 * 1000, tz=timezone),
        GOLD_NEWS_JOB_ID: CronSchedule(kind="every", every_ms=60 * 60 * 1000, tz=timezone),
        GOLD_FOLLOWUP_JOB_ID: CronSchedule(kind="every", every_ms=15 * 60 * 1000, tz=timezone),
        MORNING_BRIEFING_JOB_ID: CronSchedule(kind="cron", expr="30 7 * * 1-5", tz=timezone),
        SCORECARD_JOB_ID: CronSchedule(kind="cron", expr="0 21 * * 5", tz=timezone),
        DAILY_WRAP_JOB_ID: CronSchedule(kind="cron", expr="0 21 * * 1-5", tz=timezone),
        TRADE_MANAGEMENT_JOB_ID: CronSchedule(kind="every", every_ms=60 * 1000, tz=timezone),
        TRADABILITY_JOB_ID: CronSchedule(kind="every", every_ms=30 * 60 * 1000, tz=timezone),
        EVENT_MONITOR_JOB_ID: CronSchedule(kind="every", every_ms=15 * 60 * 1000, tz=timezone),
        OPPORTUNITY_SCAN_JOB_ID: CronSchedule(kind="every", every_ms=30 * 60 * 1000, tz=timezone),
        COT_REFRESH_JOB_ID: CronSchedule(kind="every", every_ms=6 * 60 * 60 * 1000, tz=timezone),
    }
    for job_id in TRADING_CRON_JOB_IDS:
        register(
            CronJob(
                id=job_id,
                name=job_id,
                schedule=schedules[job_id],
                payload=CronPayload(kind="system_event"),
            )
        )
    logger.info("Cron: registered gold trading monitor jobs")


async def run_gold_news_job() -> str | None:
    from mokli.trading.agents.news_macro import run_news_macro_agent

    news = run_news_macro_agent()
    if news.news_risk in {"high", "medium"} and news.upcoming_events:
        first = news.upcoming_events[0]
        if isinstance(first, dict):
            raw_title = cast(dict[str, object], first).get("title")
        else:
            raw_title = getattr(first, "title", None)
        title = raw_title if isinstance(raw_title, str) and raw_title else "event"
        return f"Gold news watch: {news.news_risk} — {title}"
    return None


async def run_gold_followup_job() -> list[dict[str, object]] | None:
    """Return outcome transition alerts (Telegram HTML + WhatsApp plain)."""
    from mokli.trading.recommendations.outcome_delivery import collect_outcome_alerts

    alerts = await collect_outcome_alerts()
    if not alerts:
        return None
    payloads: list[dict[str, object]] = []
    for alert in alerts:
        metadata = dict(alert.metadata or {})
        payloads.append(
            {
                "content": alert.content,
                "metadata": metadata,
            }
        )
    return payloads


_last_management_keys: set[str] = set()


async def run_morning_briefing_job() -> str:
    news = await run_gold_news_job()
    if news:
        return f"Morning briefing: {news}"
    return "Morning briefing: no high-impact events on the calendar"


async def run_scorecard_job() -> str:
    from mokli.trading.reports.scorecard import build_scorecard

    card = build_scorecard([], period="week")
    return (
        f"Scorecard {card['period']}: trades={card['trades']} "
        f"win_rate={card['win_rate']:.2f} pnl={card['pnl']:.2f}"
    )


async def run_daily_wrap_job() -> str:
    from datetime import UTC, datetime

    from mokli.trading.reports.behaviour import daily_wrap_prompt

    day = datetime.now(tz=UTC).date().isoformat()
    prompt = daily_wrap_prompt(day)
    return f"Daily wrap {prompt['day']}: {prompt['prompt_key']}"


async def run_trade_management_job() -> str | None:
    global _last_management_keys
    from mokli.trading.management.engine import run_management_cycle

    summary = await run_management_cycle()
    actions_raw = summary.get("actions")
    rows: list[dict[str, object]] = []
    if isinstance(actions_raw, list):
        for item in cast(list[object], actions_raw):
            if isinstance(item, dict):
                rows.append(cast(dict[str, object], item))
    if not rows:
        _last_management_keys = set()
        return None

    def _cell(row: dict[str, object], key: str) -> str:
        value = row.get(key)
        return "" if value is None else str(value)

    keys = {f"{_cell(row, 'ticket')}:{_cell(row, 'kind')}:{_cell(row, 'stop')}:{_cell(row, 'volume')}" for row in rows}
    if keys == _last_management_keys:
        return None
    _last_management_keys = keys
    kinds = ", ".join(sorted({_cell(row, "kind") for row in rows}))
    return f"Trade management: {kinds}"


async def run_trading_cron_job(name: str) -> str | list[dict[str, object]] | None:
    if name == GOLD_NEWS_JOB_ID:
        return await run_gold_news_job()
    if name == GOLD_FOLLOWUP_JOB_ID:
        return await run_gold_followup_job()
    if name == GOLD_SCAN_JOB_ID:
        return await run_gold_scan_job()
    if name == MORNING_BRIEFING_JOB_ID:
        return await run_morning_briefing_job()
    if name == SCORECARD_JOB_ID:
        return await run_scorecard_job()
    if name == DAILY_WRAP_JOB_ID:
        return await run_daily_wrap_job()
    if name == TRADE_MANAGEMENT_JOB_ID:
        return await run_trade_management_job()
    if name == TRADABILITY_JOB_ID:
        return await run_tradability_job()
    if name == EVENT_MONITOR_JOB_ID:
        return await run_event_monitor_job()
    if name == OPPORTUNITY_SCAN_JOB_ID:
        return await run_opportunity_scan_job()
    if name == COT_REFRESH_JOB_ID:
        return await run_cot_job()
    return None


async def run_tradability_job() -> str:
    from mokli.trading.bots.opportunity import tradability

    state = tradability(spread_points=0.0, max_spread=60.0, news_risk="low")
    return f"Tradability: {state['notice_key']}"


async def run_event_monitor_job() -> str | None:
    from datetime import UTC, datetime

    from mokli.trading.intel.calendar_view import upcoming_rows
    from mokli.trading.news.forex_factory import fetch_upcoming_events

    try:
        events = fetch_upcoming_events()
    except Exception:
        logger.exception("Event monitor calendar fetch failed")
        return None
    soon = upcoming_rows(events, now=datetime.now(tz=UTC), within_minutes=30)
    if not soon:
        return None
    return "Event monitor: calendar.soon"


async def run_cot_job() -> str | None:
    from mokli.trading.intel.cot import load_gold_cot

    snapshot = load_gold_cot()
    if not snapshot.get("available"):
        return None
    return f"COT: {snapshot['notice_key']}"


async def run_opportunity_scan_job() -> str | None:
    from mokli.trading.bots.opportunity import scan_opportunities

    names = scan_opportunities(price=None, atr=0.0, compressed=True)
    if not names:
        return None
    return "Opportunity scan: " + ", ".join(names)


async def run_gold_scan_job() -> str | None:
    """Run one bot coordinator cycle; return alert text if any."""
    try:
        outcome = run_bot_cycle()
    except Exception:
        logger.exception("Gold scan cron failed")
        return None
    if not outcome.alerts:
        return None
    return "Gold scanner:\n" + "\n".join(f"• {line}" for line in outcome.alerts[:3])
