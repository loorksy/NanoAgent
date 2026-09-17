"""Trading background cron registration."""

from __future__ import annotations

import asyncio

from nanobot.cron.types import CronJob, CronPayload, CronSchedule
from nanobot.trading.cron import (
    GOLD_FOLLOWUP_JOB_ID,
    GOLD_NEWS_JOB_ID,
    GOLD_SCAN_JOB_ID,
    register_trading_cron_jobs,
    run_gold_news_job,
)
from nanobot.trading.types import EconomicEvent, NewsMacroResult


class _FakeCron:
    def __init__(self) -> None:
        self.jobs: dict[str, CronJob] = {}

    def register_system_job(self, job: CronJob) -> CronJob:
        self.jobs[job.id] = job
        return job

    def remove_system_job(self, job_id: str) -> bool:
        return self.jobs.pop(job_id, None) is not None


def test_register_trading_cron_jobs_disabled_removes_jobs() -> None:
    cron = _FakeCron()
    cron.jobs[GOLD_SCAN_JOB_ID] = CronJob(
        id=GOLD_SCAN_JOB_ID,
        name=GOLD_SCAN_JOB_ID,
        schedule=CronSchedule(kind="every", every_ms=1000),
        payload=CronPayload(kind="system_event"),
    )

    register_trading_cron_jobs(cron, enabled=False)

    assert GOLD_SCAN_JOB_ID not in cron.jobs
    assert GOLD_NEWS_JOB_ID not in cron.jobs
    assert GOLD_FOLLOWUP_JOB_ID not in cron.jobs


def test_register_trading_cron_jobs_enabled_registers_all() -> None:
    cron = _FakeCron()

    register_trading_cron_jobs(cron, enabled=True)

    assert set(cron.jobs) == {GOLD_SCAN_JOB_ID, GOLD_NEWS_JOB_ID, GOLD_FOLLOWUP_JOB_ID}


def test_run_gold_news_job_reads_economic_event_title(monkeypatch) -> None:
    news = NewsMacroResult(
        news_risk="high",
        bias_impact="mixed",
        affected_currencies=["USD"],
        upcoming_events=[
            EconomicEvent(title="US CPI", time="2026-01-01T12:00:00Z", impact="high"),
        ],
        trade_allowed=False,
        reason="high-impact calendar",
    )
    monkeypatch.setattr(
        "nanobot.trading.agents.news_macro.run_news_macro_agent",
        lambda: news,
    )

    alert = asyncio.run(run_gold_news_job())

    assert alert == "Gold news watch: high — US CPI"
