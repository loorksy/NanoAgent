import pytest
from websockets.datastructures import Headers
from websockets.http11 import Request

from nanobot.trading.chart_host_bridge import get_chart_host_bridge
from nanobot.trading.chart_host_token import mint_chart_host_page_token
from nanobot.webui.trading_api import (
    handle_trading_chart_host_poll,
    handle_trading_chart_host_submit,
)


@pytest.fixture(autouse=True)
def chart_host_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NANOBOT_CHART_HOST_TOKEN", "test-chart-host-secret-123456")


def _request(path: str, *, token: str | None = None, ws_token: str | None = None) -> Request:
    headers = Headers()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(path, headers)
    if ws_token:
        setattr(request, "_nanobot_chart_host_ws_token", ws_token)
    return request


def test_chart_host_poll_requires_auth() -> None:
    response = handle_trading_chart_host_poll(_request("/api/trading/chart-host/poll"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chart_host_submit_accepts_ws_token() -> None:
    token = mint_chart_host_page_token(ttl_sec=120)
    assert token
    bridge = get_chart_host_bridge()
    capture_id = "ws-submit-cap"
    bridge.begin(capture_id, timeframes=["15m"], interval="15m")

    request = _request(
        "/api/trading/chart-host/submit",
        ws_token=token,
    )
    setattr(
        request,
        "_nanobot_webui_mutation_payload",
        {
            "captureId": capture_id,
            "frames": [{"timeframe": "15m", "image": "aGVsbG8="}],
        },
    )
    response = handle_trading_chart_host_submit(request)
    assert response.status_code == 200
    assert b'"ok": true' in response.body


@pytest.mark.asyncio
async def test_chart_host_submit_accepts_bearer_token() -> None:
    token = mint_chart_host_page_token(ttl_sec=120)
    assert token
    bridge = get_chart_host_bridge()
    capture_id = "bearer-submit-cap"
    bridge.begin(capture_id, timeframes=["1h"], interval="1h")

    request = _request(
        "/api/trading/chart-host/submit",
        token=token,
    )
    setattr(
        request,
        "_nanobot_webui_mutation_payload",
        {
            "captureId": capture_id,
            "frames": [{"timeframe": "1h", "image": "aGVsbG8="}],
        },
    )
    response = handle_trading_chart_host_submit(request)
    assert response.status_code == 200
