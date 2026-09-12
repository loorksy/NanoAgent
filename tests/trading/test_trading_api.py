from websockets.http11 import Request

from nanobot.webui.trading_api import (
    handle_trading_klines,
    handle_trading_performance,
    handle_trading_status,
)


def _request(path: str) -> Request:
    return Request("GET", path, [])


def test_trading_status_without_oanda() -> None:
    response = handle_trading_status(_request("/api/trading/status"))
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "XAUUSD" in body
    assert "oanda_configured" in body


def test_trading_performance_payload() -> None:
    response = handle_trading_performance(_request("/api/trading/performance"))
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "totalRecommendations" in body
    assert "paperActions" in body


def test_trading_klines_unconfigured() -> None:
    response = handle_trading_klines(
        _request("/api/trading/klines?symbol=XAUUSD&interval=1h&limit=10"),
    )
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "candles" in body
