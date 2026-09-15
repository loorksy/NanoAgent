#!/usr/bin/env python3
"""VPS smoke test for chart-host WS submit auth and capture roundtrip."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

import websockets


async def test_ws_submit_auth(base_url: str, page_token: str) -> None:
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_url}/?token={page_token}&client_id=chart-host-test"
    request_id = str(uuid.uuid4())
    frame = {
        "type": "webui_request",
        "request_id": request_id,
        "action": "trading.chart_host_submit",
        "payload": {
            "captureId": "nonexistent-capture-id",
            "frames": [{"timeframe": "15m", "image": "aGVsbG8="}],
        },
    }
    async with websockets.connect(ws_url) as socket:
        await socket.send(json.dumps(frame))
        while True:
            raw = await asyncio.wait_for(socket.recv(), timeout=15)
            payload = json.loads(raw)
            if payload.get("event") != "webui_response" or payload.get("request_id") != request_id:
                continue
            error = payload.get("error") or {}
            status = error.get("status")
            message = error.get("message")
            if status == 401 or message == "unauthorized":
                raise SystemExit(f"FAIL: WS submit still returns 401 ({payload})")
            if status == 404 or "No pending" in str(message):
                print("PASS: WS submit authorized (got expected 404 for missing capture)")
                return
            if payload.get("ok"):
                print("PASS: WS submit authorized (unexpected ok for missing capture)")
                return
            raise SystemExit(f"FAIL: unexpected WS submit response: {payload}")


async def test_capture_roundtrip(base_url: str, page_token: str) -> None:
    """Run full chart-host capture via the smoke endpoint."""
    import urllib.request

    smoke_url = f"{base_url}/api/trading/chart-host/smoke?interval=15m"
    req = urllib.request.Request(smoke_url, headers={"Authorization": f"Bearer {page_token}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    if not body.get("ok"):
        raise SystemExit(f"FAIL: chart-host smoke capture failed: {body}")
    print(
        "PASS: chart-host smoke capture",
        f"frames={body.get('frameCount')} timeframes={body.get('timeframes')}",
    )


async def main() -> None:
    base_url = os.environ.get("CHART_HOST_APP_URL", "https://nanoagent.lork.cloud")
    sys.path.insert(0, os.environ.get("NANOAGENT_ROOT", "/opt/nanoagent"))
    from nanobot.trading.chart_host_token import mint_chart_host_page_token

    page_token = mint_chart_host_page_token(ttl_sec=600)
    if not page_token:
        raise SystemExit("FAIL: could not mint chart-host page token (check NANOBOT_CHART_HOST_TOKEN)")
    print(f"page_token minted ({len(page_token)} chars)")
    await test_ws_submit_auth(base_url, page_token)
    await test_capture_roundtrip(base_url, page_token)


if __name__ == "__main__":
    asyncio.run(main())
