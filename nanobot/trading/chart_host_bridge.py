"""Server-side bridge between chart-host page polls and orchestrator capture waits."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any

from nanobot.trading.chart_capture import validate_chart_frames

_DEFAULT_TIMEOUT_SEC = 90.0
_JOB_TTL_SEC = 120.0


@dataclass
class _CaptureWaiter:
    event: threading.Event
    result: dict[str, Any] | None = None
    cancelled: bool = False


class ChartHostCaptureBridge:
    def __init__(self) -> None:
        self._pending: dict[str, _CaptureWaiter] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._queued: list[str] = []

    def begin(self, capture_id: str, *, timeframes: list[str], interval: str = "15m") -> None:
        self._expire_stale()
        existing = self._pending.get(capture_id)
        if existing is not None and not existing.event.is_set():
            existing.cancelled = True
            existing.event.set()
        self._pending[capture_id] = _CaptureWaiter(event=threading.Event())
        self._jobs[capture_id] = {
            "captureId": capture_id,
            "timeframes": list(timeframes),
            "interval": interval,
            "createdAt": time.time(),
        }
        if capture_id not in self._queued:
            self._queued.append(capture_id)

    async def wait(self, capture_id: str, *, timeout: float = _DEFAULT_TIMEOUT_SEC) -> dict[str, Any]:
        self._expire_stale()
        waiter = self._pending.get(capture_id)
        if waiter is None:
            self.begin(capture_id, timeframes=["15m"])
            waiter = self._pending[capture_id]
        loop = asyncio.get_running_loop()
        signaled = await loop.run_in_executor(None, waiter.event.wait, timeout)
        try:
            if not signaled or waiter.cancelled:
                return {"frames": []}
            return waiter.result or {"frames": []}
        finally:
            self._pending.pop(capture_id, None)
            self._jobs.pop(capture_id, None)
            if capture_id in self._queued:
                self._queued.remove(capture_id)

    def poll_job(self) -> dict[str, Any] | None:
        self._expire_stale()
        while self._queued:
            capture_id = self._queued[0]
            job = self._jobs.get(capture_id)
            if job is None:
                self._queued.pop(0)
                continue
            return dict(job)
        return None

    def submit(self, capture_id: str, payload: dict[str, Any]) -> bool:
        self._expire_stale()
        waiter = self._pending.get(capture_id)
        if waiter is None or waiter.event.is_set():
            return False
        frames_raw = payload.get("frames")
        if not isinstance(frames_raw, list):
            frames_raw = []
        try:
            frames = validate_chart_frames(frames_raw)
        except Exception:
            return False
        waiter.result = {"frames": frames}
        waiter.event.set()
        self._pending.pop(capture_id, None)
        self._jobs.pop(capture_id, None)
        if capture_id in self._queued:
            self._queued.remove(capture_id)
        return True

    def _expire_stale(self) -> None:
        now = time.time()
        stale = [
            capture_id
            for capture_id, job in self._jobs.items()
            if now - float(job.get("createdAt") or now) > _JOB_TTL_SEC
        ]
        for capture_id in stale:
            waiter = self._pending.get(capture_id)
            if waiter is not None and not waiter.event.is_set():
                waiter.cancelled = True
                waiter.event.set()
            self._pending.pop(capture_id, None)
            self._jobs.pop(capture_id, None)
            if capture_id in self._queued:
                self._queued.remove(capture_id)


_BRIDGE = ChartHostCaptureBridge()


def get_chart_host_bridge() -> ChartHostCaptureBridge:
    return _BRIDGE
