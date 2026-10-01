"""Trading background cron registration."""

from __future__ import annotations

import asyncio
import time

from mokli.cron.types import CronJob, CronPayload, CronSchedule
from mokli.trading.bots.coordinator import BotCycleResult
from mokli.trading.cron import (
    GOLD_FOLLOWUP_JOB_ID,
    GOLD_NEWS_JOB_ID,
    GOLD_SCAN_JOB_ID,
    TRADING_CRON_JOB_IDS,
    register_trading_cron_jobs,
    run_cot_job,
    run_event_monitor_job,
    run_gold_news_job,
    run_gold_scan_job,
)
from mokli.trading.types import EconomicEvent, NewsMacroResult


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

    assert set(cron.jobs) == set(TRADING_CRON_JOB_IDS)


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
        "mokli.trading.agents.news_macro.run_news_macro_agent",
        lambda: news,
    )

    alert = asyncio.run(run_gold_news_job())

    assert alert == "Gold news watch: high — US CPI"


def test_trading_cron_downloads_leave_the_event_loop_free(monkeypatch) -> None:
    """Calendar, COT, news, and the gold scan wait on a worker, not the loop."""

    def slow(result: object) -> object:
        def _run() -> object:
            time.sleep(0.2)
            return result

        return _run

    news = NewsMacroResult(
        news_risk="low",
        bias_impact="mixed",
        affected_currencies=["USD"],
        upcoming_events=[],
        trade_allowed=True,
        reason="quiet",
    )
    monkeypatch.setattr(
        "mokli.trading.agents.news_macro.run_news_macro_agent",
        slow(news),
    )
    monkeypatch.setattr(
        "mokli.trading.news.forex_factory.fetch_upcoming_events",
        slow([]),
    )
    monkeypatch.setattr(
        "mokli.trading.intel.cot.load_gold_cot",
        slow({"available": False, "notice_key": "cot.bias_neutral"}),
    )
    monkeypatch.setattr("mokli.trading.cron.run_bot_cycle", slow(BotCycleResult()))

    async def _one(job) -> None:
        order: list[str] = []

        async def _mark() -> None:
            await asyncio.sleep(0.05)
            order.append("task")

        started = time.perf_counter()
        marker = asyncio.create_task(_mark())
        await job()
        await marker
        order.append("job")
        assert order == ["task", "job"]
        assert time.perf_counter() - started < 0.35

    async def _all() -> None:
        await _one(run_gold_news_job)
        await _one(run_event_monitor_job)
        await _one(run_cot_job)
        await _one(run_gold_scan_job)

    asyncio.run(_all())
