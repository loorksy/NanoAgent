"""In-memory bridge between WebUI TradingView snapshots and the orchestrator."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.context import current_request_session_key
from nanobot.trading.agents.visual_capture import CaptureFn

if TYPE_CHECKING:
    from nanobot.trading.stage_delivery import TradingStagePublisher

_CAPTURE_TTL_SEC = 30.0
_DEFAULT_TIMEOUT_SEC = 8.0


class ChartCaptureBridge:
    """Wait for one WebUI snapshot upload keyed by capture id."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._submitted_at: dict[str, float] = {}

    def begin(self, capture_id: str) -> None:
        self._expire_stale()
        if capture_id in self._pending and not self._pending[capture_id].done():
            self._pending[capture_id].cancel()
        self._pending[capture_id] = asyncio.get_running_loop().create_future()

    async def wait(self, capture_id: str, *, timeout: float = _DEFAULT_TIMEOUT_SEC) -> dict[str, Any]:
        self._expire_stale()
        future = self._pending.get(capture_id)
        if future is None:
            self.begin(capture_id)
            future = self._pending[capture_id]
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except TimeoutError:
            future.cancel()
            self._pending.pop(capture_id, None)
            return {"frames": []}
        finally:
            self._pending.pop(capture_id, None)

    def submit(self, capture_id: str, payload: dict[str, Any]) -> bool:
        self._expire_stale()
        future = self._pending.get(capture_id)
        if future is None or future.done():
            return False
        frames = payload.get("frames")
        if not isinstance(frames, list):
            frames = []
        future.set_result({"frames": frames})
        self._submitted_at[capture_id] = time.time()
        self._pending.pop(capture_id, None)
        return True

    def _expire_stale(self) -> None:
        now = time.time()
        stale = [key for key, ts in self._submitted_at.items() if now - ts > _CAPTURE_TTL_SEC]
        for key in stale:
            self._submitted_at.pop(key, None)
        for key, future in list(self._pending.items()):
            if future.done():
                self._pending.pop(key, None)


_BRIDGE = ChartCaptureBridge()


def get_chart_capture_bridge() -> ChartCaptureBridge:
    return _BRIDGE


def submit_chart_capture(capture_id: str, payload: dict[str, Any]) -> bool:
    return _BRIDGE.submit(capture_id, payload)


def create_chart_capture_fn(
    session_key: str,
    publisher: TradingStagePublisher | None,
) -> CaptureFn:
    async def capture(timeframes: list[str]) -> dict[str, Any]:
        capture_id = str(uuid.uuid4())
        if publisher is not None and publisher.is_web_channel:
            await publisher.request_chart_capture(
                capture_id,
                session_key=session_key,
                timeframes=timeframes,
            )
        return await _BRIDGE.wait(capture_id)

    return capture


def resolve_visual_capture(publisher: TradingStagePublisher | None) -> CaptureFn | None:
    session_key = current_request_session_key()
    if not session_key or publisher is None or not publisher.is_web_channel:
        return None
    return create_chart_capture_fn(session_key, publisher)
