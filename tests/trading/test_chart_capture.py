import asyncio

import pytest

from nanobot.trading.agents.visual_capture import capture_visual_evidence
from nanobot.trading.chart_capture import (
    get_chart_capture_bridge,
    submit_chart_capture,
)


@pytest.mark.asyncio
async def test_chart_capture_bridge_roundtrip():
    bridge = get_chart_capture_bridge()
    capture_id = "cap-test-1"
    bridge.begin(capture_id, session_key="webui:test")

    async def submit_later() -> None:
        await asyncio.sleep(0.05)
        assert submit_chart_capture(
            capture_id,
            {"frames": [{"timeframe": "15m", "context": "stub"}]},
            session_key="webui:test",
        )

    waiter = asyncio.create_task(bridge.wait(capture_id, timeout=1.0))
    await submit_later()
    payload = await waiter
    assert payload["frames"][0]["timeframe"] == "15m"


@pytest.mark.asyncio
async def test_capture_visual_evidence_with_callback():
    async def capture(timeframes: list[str]) -> dict:
        return {
            "frames": [
                {"timeframe": tf, "context": f"frame {tf}"}
                for tf in timeframes
            ],
        }

    visual, snapshots = await capture_visual_evidence("15m", capture=capture)
    assert visual.state == "checked"
    assert "15m" in visual.captured
    assert snapshots
