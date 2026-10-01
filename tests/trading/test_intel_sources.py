"""Independent gold-intel reads overlap. No live network."""

from __future__ import annotations

import asyncio

import pytest

from mokli.agent.tools import trading_intel
from mokli.trading.intel.telegram_scraper import TelegramHeadlineSource


@pytest.mark.asyncio
async def test_intel_sources_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[str] = []
    release = asyncio.Event()

    async def _wait(name: str) -> list[object]:
        started.append(name)
        if len(started) == 4:
            release.set()
        await release.wait()
        return []

    monkeypatch.setattr(trading_intel, "fetch_rss_headlines", lambda: _wait("rss"))
    monkeypatch.setattr(trading_intel, "fetch_vip_statements", lambda: _wait("vip"))
    monkeypatch.setattr(trading_intel, "fetch_economic_calendar", lambda: _wait("calendar"))

    async def _recent(self: TelegramHeadlineSource, *, limit: int = 8) -> list[object]:
        del self, limit
        return await _wait("telegram")

    monkeypatch.setattr(TelegramHeadlineSource, "fetch_recent", _recent)

    headlines, vips, calendar, telegram_rows, _telegram = await asyncio.wait_for(
        trading_intel.collect_intel_sources(),
        timeout=1,
    )
    assert started == ["rss", "vip", "calendar", "telegram"]
    assert headlines == []
    assert vips == []
    assert calendar == []
    assert telegram_rows == []
