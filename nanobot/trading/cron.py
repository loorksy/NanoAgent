"""Cron hooks for gold trading monitors."""

from __future__ import annotations

import logging

from nanobot.cron.types import CronJob, CronPayload, CronSchedule
from nanobot.trading.bots.coordinator import run_bot_cycle

logger = logging.getLogger(__name__)

GOLD_SCAN_JOB_ID = "gold_scan"
GOLD_NEWS_JOB_ID = "gold_news"
GOLD_FOLLOWUP_JOB_ID = "gold_rec_followup"


def register_trading_cron_jobs(cron_service: object, timezone: str = "UTC") -> None:
    """Register background gold scanner (every 30 minutes)."""
    register = getattr(cron_service, "register_system_job", None)
    if register is None:
        return
    for job_id, every_ms in (
        (GOLD_SCAN_JOB_ID, 30 * 60 * 1000),
        (GOLD_NEWS_JOB_ID, 60 * 60 * 1000),
        (GOLD_FOLLOWUP_JOB_ID, 15 * 60 * 1000),
    ):
        register(
            CronJob(
                id=job_id,
                name=job_id,
                schedule=CronSchedule(kind="every", every_ms=every_ms, tz=timezone),
                payload=CronPayload(kind="system_event"),
            )
        )
    logger.info("Cron: registered gold trading monitor jobs")


async def run_gold_news_job() -> str | None:
    from nanobot.trading.agents.news_macro import run_news_macro_agent

    news = run_news_macro_agent()
    if news.news_risk in {"high", "medium"} and news.upcoming_events:
        title = news.upcoming_events[0].get("title", "event")
        return f"Gold news watch: {news.news_risk} — {title}"
    return None


async def run_gold_followup_job() -> str | None:
    from nanobot.trading.recommendations.followup import latest_open_recommendation

    open_rec = latest_open_recommendation()
    if not open_rec:
        return None
    return (
        f"Open gold {open_rec.get('direction', '').upper()} still active — "
        f"{open_rec.get('summary', '')}"
    )


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
