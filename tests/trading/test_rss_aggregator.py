"""RSS feed downloads overlap. No live network."""

from __future__ import annotations

import asyncio

import pytest

from mokli.trading.intel import rss_aggregator


@pytest.mark.asyncio
async def test_rss_feed_downloads_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[str] = []
    release = asyncio.Event()

    class _Response:
        def __init__(self, url: str) -> None:
            self.text = url

    class _Client:
        def __init__(self, timeout: float) -> None:
            del timeout

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str) -> _Response:
            started.append(url)
            if len(started) == 3:
                release.set()
            await release.wait()
            return _Response(url)

    monkeypatch.setattr(rss_aggregator, "module_available", lambda name: name != "aiohttp")
    monkeypatch.setattr("httpx.AsyncClient", _Client)

    bodies = await asyncio.wait_for(
        rss_aggregator._fetch_bodies(("https://a.test", "https://b.test", "https://c.test"), 1.0),
        timeout=1,
    )
    assert list(bodies) == ["https://a.test", "https://b.test", "https://c.test"]
    assert started == ["https://a.test", "https://b.test", "https://c.test"]
