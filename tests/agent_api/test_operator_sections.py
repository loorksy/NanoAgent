"""Performance, briefing, and token-burn sections on /api/v2."""

from __future__ import annotations

import asyncio
import threading
import time

from aiohttp.test_utils import TestClient

from agent_api.conftest import auth


async def test_performance_briefing_and_usage_are_readable(client: TestClient) -> None:
    performance = await client.get("/api/v2/performance", headers=auth())
    assert performance.status == 200
    body = await performance.json()
    assert "totalRecommendations" in body
    assert "directionBreakdown" in body
    assert "outcomeBreakdown" in body
    assert "paperActions" in body

    briefing = await client.get("/api/v2/briefing?locale=ar", headers=auth())
    assert briefing.status == 200
    brief = await briefing.json()
    assert brief["symbol"] == "XAUUSD"
    assert "summary" in brief
    assert set(brief["quote"]) == {"mid", "bid", "ask"}

    usage = await client.get("/api/v2/usage?days=30", headers=auth())
    assert usage.status == 200
    burned = await usage.json()
    assert "total_tokens_30d" in burned
    assert "providers_30d" in burned
    assert "days" in burned


async def test_briefing_and_performance_leave_the_event_loop_free(
    client: TestClient, monkeypatch,
) -> None:
    """Operator pages wait for the broker quote off the event loop."""
    from mokli.trading.oanda import OandaQuote

    order: list[str] = []

    def slow_quote(symbol: str = "XAUUSD") -> OandaQuote:
        del symbol
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        return OandaQuote(symbol="XAUUSD", bid=2400.0, ask=2400.4, mid=2400.2, tradeable=True)

    monkeypatch.setattr("mokli.trading.market_context.live_analysis_quote", slow_quote)

    async def one(path: str) -> None:
        order.clear()

        async def tick() -> None:
            await asyncio.sleep(0.05)
            order.append("tick")

        pending = asyncio.create_task(tick())
        started = time.perf_counter()
        response = await client.get(path, headers=auth())
        await pending
        assert response.status == 200
        body = await response.json()
        assert order[0] == "tick"
        assert "worker" in order
        assert time.perf_counter() - started < 0.35
        if path.startswith("/api/v2/briefing"):
            assert body["quote"]["mid"] == 2400.2
        else:
            assert "totalRecommendations" in body

    await one("/api/v2/briefing?locale=ar")
    await one("/api/v2/performance")


async def test_usage_overview_journal_and_log_leave_the_event_loop_free(
    client: TestClient, monkeypatch,
) -> None:
    """Operator pages that read a store wait off the event loop."""
    order: list[str] = []

    def _mark() -> None:
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )

    def slow_usage(*, days: int = 371, timezone_name: str | None = None) -> dict[str, object]:
        del days, timezone_name
        time.sleep(0.2)
        _mark()
        return {"total_tokens_30d": 7, "days": [], "providers_30d": []}

    def slow_journal() -> list[dict[str, object]]:
        time.sleep(0.2)
        _mark()
        return [{"id": "j1"}]

    def slow_query(self: object, **kwargs: object) -> list[object]:
        del self, kwargs
        time.sleep(0.2)
        _mark()
        return []

    monkeypatch.setattr("mokli.llm_usage.llm_usage_payload", slow_usage)
    monkeypatch.setattr("mokli.agent_api.routes.log.journal_entries", slow_journal)
    monkeypatch.setattr("mokli.agent_api.event_log.EventLog.query", slow_query)

    async def one(path: str, check) -> None:
        order.clear()

        async def tick() -> None:
            await asyncio.sleep(0.05)
            order.append("tick")

        pending = asyncio.create_task(tick())
        started = time.perf_counter()
        response = await client.get(path, headers=auth())
        await pending
        assert response.status == 200
        body = await response.json()
        assert order[0] == "tick"
        assert "worker" in order
        assert time.perf_counter() - started < 0.35
        check(body)

    await one(
        "/api/v2/usage?days=30",
        lambda body: body["total_tokens_30d"] == 7,
    )
    await one(
        "/api/v2/settings/overview",
        lambda body: body["usage"]["total_tokens_30d"] == 7 and body["product"] == "Mokli",
    )
    await one(
        "/api/v2/log/journal",
        lambda body: body["entries"] == [{"id": "j1"}],
    )
    await one(
        "/api/v2/log",
        lambda body: "entries" in body,
    )


async def test_operator_sections_require_a_token(client: TestClient) -> None:
    for path in ("/api/v2/performance", "/api/v2/briefing", "/api/v2/usage"):
        response = await client.get(path)
        assert response.status == 401
