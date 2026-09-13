"""Trading background cron registration."""

from __future__ import annotations

from nanobot.cron.types import CronJob, CronPayload, CronSchedule
from nanobot.trading.cron import (
    GOLD_FOLLOWUP_JOB_ID,
    GOLD_NEWS_JOB_ID,
    GOLD_SCAN_JOB_ID,
    register_trading_cron_jobs,
)


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
