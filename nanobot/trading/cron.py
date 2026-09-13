"""Cron hooks for gold trading monitors."""

from __future__ import annotations

import logging

from nanobot.cron.types import CronJob, CronPayload, CronSchedule
from nanobot.trading.bots.coordinator import run_bot_cycle

logger = logging.getLogger(__name__)

GOLD_SCAN_JOB_ID = "gold_scan"
GOLD_NEWS_JOB_ID = "gold_news"
GOLD_FOLLOWUP_JOB_ID = "gold_rec_followup"


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
    job_ids = (GOLD_SCAN_JOB_ID, GOLD_NEWS_JOB_ID, GOLD_FOLLOWUP_JOB_ID)
    if remove is not None:
        for job_id in job_ids:
            remove(job_id)
    if not enabled or register is None:
        if not enabled:
            logger.info("Cron: gold trading monitor jobs disabled (opt-in via gateway.tradingCron.enabled)")
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
        first = news.upcoming_events[0]
        title = getattr(first, "title", None) or (
            first.get("title", "event") if isinstance(first, dict) else "event"
        )
        return f"Gold news watch: {news.news_risk} — {title}"
    return None


async def run_gold_followup_job() -> list[dict[str, object]] | None:
    """Return outcome transition alerts (Telegram HTML + WhatsApp plain)."""
    from nanobot.trading.recommendations.outcome_delivery import collect_outcome_alerts

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
