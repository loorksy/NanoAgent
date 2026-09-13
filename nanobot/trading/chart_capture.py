"""In-memory bridge between WebUI TradingView snapshots and the orchestrator."""

from __future__ import annotations

import asyncio
import base64
import re
import time
import uuid
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.context import current_request_session_key
from nanobot.trading.agents.visual_capture import CaptureFn

if TYPE_CHECKING:
    from nanobot.trading.stage_delivery import TradingStagePublisher

_CAPTURE_TTL_SEC = 30.0
_DEFAULT_TIMEOUT_SEC = 8.0
_MAX_FRAMES = 5
_MAX_FRAME_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_BYTES = 4 * 1024 * 1024
_DATA_URL_RE = re.compile(r"^data:image/(?P<fmt>[a-zA-Z0-9+.-]+);base64,(?P<data>.+)$", re.S)


class ChartCaptureError(ValueError):
    """Invalid or unauthorized chart capture submission."""


def _decode_frame_payload(raw: str) -> bytes:
    payload = raw.strip()
    if not payload:
        return b""
    if payload.startswith("data:"):
        match = _DATA_URL_RE.match(payload)
        if not match:
            raise ChartCaptureError("invalid data URL frame")
        try:
            return base64.b64decode(match.group("data"), validate=True)
        except Exception as exc:
            raise ChartCaptureError("invalid base64 frame") from exc
    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ChartCaptureError("invalid base64 frame") from exc


def validate_chart_frames(frames: list[Any]) -> list[dict[str, Any]]:
    """Normalize frames and enforce count/size limits."""
    if len(frames) > _MAX_FRAMES:
        raise ChartCaptureError(f"too many frames (max {_MAX_FRAMES})")
    normalized: list[dict[str, Any]] = []
    total_bytes = 0
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ChartCaptureError(f"frame {index} must be an object")
        raw = frame.get("image") or frame.get("dataUrl")
        if raw is not None and not isinstance(raw, str):
            raise ChartCaptureError(f"frame {index} image must be a string")
        size = 0
        if isinstance(raw, str) and raw.strip():
            data = _decode_frame_payload(raw)
            size = len(data)
            if size > _MAX_FRAME_BYTES:
                raise ChartCaptureError(f"frame {index} exceeds size limit")
            total_bytes += size
            if total_bytes > _MAX_TOTAL_BYTES:
                raise ChartCaptureError("total chart capture payload too large")
        normalized.append(dict(frame))
    return normalized


class ChartCaptureBridge:
    """Wait for one WebUI snapshot upload keyed by capture id."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._owners: dict[str, str] = {}
        self._submitted_at: dict[str, float] = {}

    def begin(self, capture_id: str, *, session_key: str | None = None) -> None:
        self._expire_stale()
        if capture_id in self._pending and not self._pending[capture_id].done():
            self._pending[capture_id].cancel()
        self._pending[capture_id] = asyncio.get_running_loop().create_future()
        if session_key:
            self._owners[capture_id] = session_key

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
            self._owners.pop(capture_id, None)
            return {"frames": []}
        finally:
            self._pending.pop(capture_id, None)
            self._owners.pop(capture_id, None)

    def submit(
        self,
        capture_id: str,
        payload: dict[str, Any],
        *,
        session_key: str | None = None,
    ) -> bool:
        self._expire_stale()
        future = self._pending.get(capture_id)
        if future is None or future.done():
            return False
        owner = self._owners.get(capture_id)
        if owner and session_key and owner != session_key:
            return False
        if owner and not session_key:
            return False
        frames_raw = payload.get("frames")
        if not isinstance(frames_raw, list):
            frames_raw = []
        try:
            frames = validate_chart_frames(frames_raw)
        except ChartCaptureError:
            return False
        future.set_result({"frames": frames})
        self._submitted_at[capture_id] = time.time()
        self._pending.pop(capture_id, None)
        self._owners.pop(capture_id, None)
        return True

    def _expire_stale(self) -> None:
        now = time.time()
        stale = [key for key, ts in self._submitted_at.items() if now - ts > _CAPTURE_TTL_SEC]
        for key in stale:
            self._submitted_at.pop(key, None)
        for key, future in list(self._pending.items()):
            if future.done():
                self._pending.pop(key, None)
                self._owners.pop(key, None)


_BRIDGE = ChartCaptureBridge()


def get_chart_capture_bridge() -> ChartCaptureBridge:
    return _BRIDGE


def submit_chart_capture(
    capture_id: str,
    payload: dict[str, Any],
    *,
    session_key: str | None = None,
) -> bool:
    return _BRIDGE.submit(capture_id, payload, session_key=session_key)


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
