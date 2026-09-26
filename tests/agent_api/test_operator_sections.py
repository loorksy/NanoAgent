"""Performance, briefing, and token-burn sections on /api/v2."""

from __future__ import annotations

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


async def test_operator_sections_require_a_token(client: TestClient) -> None:
    for path in ("/api/v2/performance", "/api/v2/briefing", "/api/v2/usage"):
        response = await client.get(path)
        assert response.status == 401
