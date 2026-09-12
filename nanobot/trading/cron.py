"""Cron hooks for gold trading monitors."""

from __future__ import annotations

import logging

from nanobot.cron.types import CronJob, CronPayload, CronSchedule
from nanobot.trading.bots.coordinator import run_bot_cycle

logger = logging.getLogger(__name__)

GOLD_SCAN_JOB_ID = "gold_scan"


def register_trading_cron_jobs(cron_service: object, timezone: str = "UTC") -> None:
    """Register background gold scanner (every 30 minutes)."""
    register = getattr(cron_service, "register_system_job", None)
    if register is None:
        return
    register(
        CronJob(
            id=GOLD_SCAN_JOB_ID,
            name=GOLD_SCAN_JOB_ID,
            schedule=CronSchedule(kind="every", every_ms=30 * 60 * 1000, tz=timezone),
            payload=CronPayload(kind="system_event"),
        )
    )
    logger.info("Cron: registered gold trading scan job")


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
