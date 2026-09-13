"""On-demand gold chart capture for WebUI and channel delivery."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.context import current_request_context, current_request_session_key
from nanobot.bus.events import OutboundMessage
from nanobot.trading.agents.visual_capture import capture_visual_evidence, visual_timeframes
from nanobot.trading.chart_capture import create_chart_capture_fn
from nanobot.trading.chart_photo import lead_chart_frame, write_chart_snapshot_file
from nanobot.trading.locale import locale_from_text, normalize_locale
from nanobot.trading.stage_delivery import TradingStagePublisher

_CAPTURE_ERROR = {
    "ar": {
        "webui_required": (
            "التقاط صورة الشارت يتطلب WebUI مع لوحة الشارت مفتوحة. "
            "افتح المحادثة من الواجهة ثم أعد الطلب."
        ),
        "no_frames": "لم تُلتقط أي صورة للشارت. تأكد أن لوحة الشارت مفتوحة وحاول مرة أخرى.",
    },
    "en": {
        "webui_required": (
            "Chart capture requires the WebUI with the gold chart side panel open. "
            "Open the chat in the web interface and try again."
        ),
        "no_frames": "No chart image was captured. Open the chart panel and try again.",
    },
}


def _msg(key: str, locale: str) -> str:
    loc = "ar" if normalize_locale(locale) == "ar" else "en"
    return _CAPTURE_ERROR[loc][key]


def build_chart_snapshot_artifact(
    snapshots: list[dict[str, Any]],
    *,
    interval: str,
    locale: str,
) -> dict[str, Any] | None:
    frame = lead_chart_frame(snapshots)
    if not frame:
        return None
    title = (
        f"لقطة شارت الذهب ({interval})"
        if locale == "ar"
        else f"Gold chart snapshot ({interval})"
    )
    return {
        "type": "chart_snapshot",
        "title": title,
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
    if not publisher.is_web_channel:
        return {
            "ok": False,
            "error": "webui_required",
            "message": _msg("webui_required", locale),
            "artifacts": [],
        }

    session_key = current_request_session_key() or f"{channel}:{chat_id}"
    await publisher.open_chart(interval)
    capture_fn = create_chart_capture_fn(session_key, publisher)
    requested = timeframes or visual_timeframes(interval)
    _visual, snapshots = await capture_visual_evidence(interval, capture=capture_fn)

    artifact = build_chart_snapshot_artifact(snapshots, interval=interval, locale=locale)
    if artifact is None:
        return {
            "ok": False,
            "error": "no_frames",
            "message": _msg("no_frames", locale),
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
    return json.dumps(payload, indent=2)
