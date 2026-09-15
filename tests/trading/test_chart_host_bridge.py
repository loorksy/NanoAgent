import asyncio

import pytest

from nanobot.trading.chart_host_bridge import get_chart_host_bridge


@pytest.mark.asyncio
async def test_chart_host_bridge_poll_submit_roundtrip() -> None:
    bridge = get_chart_host_bridge()
    capture_id = "host-cap-1"
    bridge.begin(capture_id, timeframes=["15m", "1h"], interval="15m")

    job = bridge.poll_job()
    assert job is not None
    assert job["captureId"] == capture_id

    async def submit_later() -> None:
        await asyncio.sleep(0.05)
        assert bridge.submit(
            capture_id,
            {"frames": [{"timeframe": "15m", "image": "aGVsbG8="}]},
        )

    waiter = asyncio.create_task(bridge.wait(capture_id, timeout=1.0))
    await submit_later()
    payload = await waiter
    assert payload["frames"][0]["timeframe"] == "15m"
