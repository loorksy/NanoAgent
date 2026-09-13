import asyncio
import base64

import pytest

from nanobot.trading.chart_capture import (
    ChartCaptureError,
    get_chart_capture_bridge,
    submit_chart_capture,
    validate_chart_frames,
)


@pytest.mark.asyncio
async def test_chart_capture_requires_matching_session_key() -> None:
    bridge = get_chart_capture_bridge()
    capture_id = "cap-session-1"
    bridge.begin(capture_id, session_key="telegram:123")

    async def submit_wrong_session() -> None:
        await asyncio.sleep(0.05)
        assert not submit_chart_capture(
            capture_id,
            {"frames": [{"timeframe": "15m", "context": "stub"}]},
            session_key="telegram:999",
        )
        assert submit_chart_capture(
            capture_id,
            {"frames": [{"timeframe": "15m", "context": "stub"}]},
            session_key="telegram:123",
        )

    waiter = asyncio.create_task(bridge.wait(capture_id, timeout=1.0))
    await submit_wrong_session()
    payload = await waiter
    assert payload["frames"][0]["timeframe"] == "15m"


def test_validate_chart_frames_rejects_too_many() -> None:
    frames = [{"timeframe": f"{index}m"} for index in range(10)]
    with pytest.raises(ChartCaptureError, match="too many frames"):
        validate_chart_frames(frames)


def test_validate_chart_frames_rejects_oversized_payload() -> None:
    huge = base64.b64encode(b"x" * (3 * 1024 * 1024)).decode("ascii")
    with pytest.raises(ChartCaptureError, match="exceeds size limit"):
        validate_chart_frames([{"image": huge}])
