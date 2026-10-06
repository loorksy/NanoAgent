"""On-demand gold chart capture for Mokli and channel delivery."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

from mokli.agent.tools.context import current_request_session_key
from mokli.bus.events import OutboundMessage
from mokli.trading.agents.visual_capture import capture_visual_evidence, visual_timeframes
from mokli.trading.chart_capture import create_chart_capture_fn
from mokli.trading.chart_host_bridge import get_chart_host_bridge
from mokli.trading.chart_host_client import chart_host_url, ensure_chart_host_tab
from mokli.trading.chart_photo import lead_chart_frame, write_chart_snapshot_file
from mokli.trading.i18n import tr
from mokli.trading.locale import locale_from_text, normalize_locale
from mokli.trading.stage_delivery import TradingStagePublisher
from mokli.trading.tool_errors import model_json


def _msg(key: str, locale: str) -> str:
    return tr(f"capture.{key}", locale)


def build_chart_snapshot_artifact(
    snapshots: list[dict[str, Any]],
    *,
    interval: str,
    locale: str,
) -> dict[str, Any] | None:
    frame = lead_chart_frame(snapshots)
    if not frame:
        return None
    loc = normalize_locale(locale)
    return {
        "type": "chart_snapshot",
        "title": tr("capture.snapshot_title", loc, interval=interval),
        "mime": "image/jpeg",
        "payload": {
            "interval": interval,
            "timeframes": [str(f.get("timeframe") or "") for f in snapshots if isinstance(f, dict)],
            "image": frame.get("image") or frame.get("dataUrl"),
        },
    }


async def deliver_chart_photo(
    bus: Any,
    *,
    channel: str,
    chat_id: str,
    snapshots: list[dict[str, Any]],
    caption: str,
    locale: str,
) -> bool:
    if bus is None or not channel or not chat_id:
        return False
    if channel not in ("telegram", "whatsapp"):
        return False
    frame = lead_chart_frame(snapshots)
    chart_path = write_chart_snapshot_file(frame)
    if not chart_path:
        return False
    metadata: dict[str, Any] = {}
    if channel == "telegram":
        metadata["parse_mode"] = "HTML"
        await bus.publish_outbound(
            OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=caption,
                media=[chart_path],
                metadata=metadata,
            )
        )
        return True
    await bus.publish_outbound(
        OutboundMessage(channel=channel, chat_id=chat_id, content=caption),
    )
    return True


async def _capture_via_chart_host(
    interval: str,
    timeframes: list[str],
) -> list[dict[str, Any]] | None:
    if not chart_host_url():
        return None
    warmed = await ensure_chart_host_tab()
    if not warmed:
        return None
    warmup_ms = int(os.environ.get("CHART_HOST_WARMUP_MS", "15000"))
    if warmup_ms > 0:
        await asyncio.sleep(warmup_ms / 1000.0)
    capture_id = str(uuid.uuid4())
    bridge = get_chart_host_bridge()
    bridge.begin(capture_id, timeframes=timeframes, interval=interval)
    payload = await bridge.wait(capture_id)
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        return None
    return [frame for frame in frames if isinstance(frame, dict)]


async def run_chart_capture(
    *,
    bus: Any,
    channel: str,
    chat_id: str,
    interval: str = "15m",
    timeframes: list[str] | None = None,
    operator_text: str = "",
) -> dict[str, Any]:
    """Capture chart frames and return wire payload with artifacts."""
    locale = locale_from_text(operator_text)
    publisher = TradingStagePublisher(
        bus, channel=channel, chat_id=chat_id, locale=locale,
    )
    requested = timeframes or visual_timeframes(interval)
    snapshots: list[dict[str, Any]]
    if chart_host_url():
        host_snapshots = await _capture_via_chart_host(interval, requested)
        if host_snapshots:
            async def host_capture_fn(_timeframes: list[str]) -> dict[str, Any]:
                return {"frames": host_snapshots}

            _visual, snapshots = await capture_visual_evidence(interval, capture=host_capture_fn)
        elif publisher.is_web_channel:
            session_key = current_request_session_key() or f"{channel}:{chat_id}"
            await publisher.open_chart(interval)
            capture_fn = create_chart_capture_fn(session_key, publisher)
            _visual, snapshots = await capture_visual_evidence(interval, capture=capture_fn)
        else:
            return {
                "ok": False,
                "error": "no_frames",
                "message": _msg("no_frames", locale),
                "hint": (
                    "The chart-host sidecar did not return a snapshot in time. "
                    "Check chart-host health and retry."
                ),
                "artifacts": [],
            }
    elif publisher.is_web_channel:
        session_key = current_request_session_key() or f"{channel}:{chat_id}"
        await publisher.open_chart(interval)
        capture_fn = create_chart_capture_fn(session_key, publisher)
        _visual, snapshots = await capture_visual_evidence(interval, capture=capture_fn)
    else:
        return {
            "ok": False,
            "error": "mokli_required",
            "message": _msg("mokli_required", locale),
            "artifacts": [],
        }

    artifact = build_chart_snapshot_artifact(snapshots, interval=interval, locale=locale)
    if artifact is None:
        return {
            "ok": False,
            "error": "no_frames",
            "message": _msg("no_frames", locale),
            "hint": (
                "The chart panel was opened but no snapshot arrived in time. "
                "On mobile, wait for the chart sheet to finish loading and retry."
            ),
            "artifacts": [],
        }

    caption = artifact["title"]
    if channel in ("telegram", "whatsapp"):
        await deliver_chart_photo(
            bus,
            channel=channel,
            chat_id=chat_id,
            snapshots=snapshots,
            caption=caption,
            locale=locale,
        )

    await publisher._agent_ui(
        "trading_artifacts",
        {"artifacts": [artifact], "locale": locale},
        content=caption,
    )

    return {
        "ok": True,
        "interval": interval,
        "locale": locale,
        "artifacts": [artifact],
        "chartSnapshots": snapshots,
    }


def chart_capture_tool_result(payload: dict[str, Any]) -> str:
    """Model-facing capture result. The image already went to the operator UI."""
    snapshots = payload.get("chartSnapshots")
    frames = len(snapshots) if isinstance(snapshots, list) else 0
    brief = {
        "ok": payload.get("ok") is True,
        "interval": payload.get("interval"),
        "frames": frames,
        "delivered": payload.get("ok") is True,
        "instruction": (
            "The chart image was delivered to the operator interface. "
            "Price levels are not in this result; do not invent them from pixels."
        ),
    }
    return model_json(brief)
