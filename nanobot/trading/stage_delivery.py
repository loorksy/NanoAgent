"""Publish trading stages: WebUI agent_ui, Telegram in-place checklist, WhatsApp one-liner."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.bus.outbound_events import ProgressEvent
from nanobot.channels.telegram.trading_progress import (
    TRADING_PROGRESS_META,
    TelegramStageRow,
    apply_stage_event,
    render_arabic_progress,
)
from nanobot.trading.stage_events import StageEvent, stage_label

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus

_WHATSAPP_PROGRESS = "⏳ جاري تحليل الذهب…"


class TradingStagePublisher:
    """Emit orchestrator stages to the active chat channel."""

    def __init__(
        self,
        bus: MessageBus | None,
        *,
        channel: str,
        chat_id: str,
    ) -> None:
        self._bus = bus
        self._channel = channel
        self._chat_id = chat_id
        self._telegram_rows: list[TelegramStageRow] = []
        self._pending: list[asyncio.Task[None]] = []
        self._whatsapp_progress_sent = False

    def sync_emit(self, event: StageEvent) -> None:
        """Sync callback for ``run_unified_chart_agent(emit=...)``."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._publish(event))
            return
        self._pending.append(loop.create_task(self._publish(event)))

    async def flush(self) -> None:
        if not self._pending:
            return
        pending = self._pending
        self._pending = []
        await asyncio.gather(*pending, return_exceptions=True)

    async def publish_team_agent(self, payload: dict[str, Any]) -> None:
        role = str(payload.get("role") or "Agent")
        status = str(payload.get("status") or "running")
        await self._agent_ui(
            "trading_team_agent",
            payload,
            content=f"{role} — {status}",
        )

    @property
    def is_web_channel(self) -> bool:
        return self._is_web()

    async def open_chart(self, interval: str = "15m") -> None:
        if not self.is_web_channel:
            return
        await self._agent_ui(
            "trading_chart_open",
            {"interval": interval, "symbol": "XAUUSD"},
            content="Opening gold chart…",
        )

    async def request_chart_capture(
        self,
        capture_id: str,
        *,
        session_key: str,
        timeframes: list[str],
    ) -> None:
        if not self.is_web_channel:
            return
        from nanobot.trading.chart_capture import get_chart_capture_bridge

        get_chart_capture_bridge().begin(capture_id)
        await self._agent_ui(
            "trading_chart_capture",
            {
                "captureId": capture_id,
                "sessionKey": session_key,
                "timeframes": timeframes,
            },
            content="Capturing chart evidence…",
        )

    async def publish_result(self, payload: dict[str, Any], *, include_card: bool = True) -> None:
        await self.flush()
        decision = str(payload.get("decision", "wait")).upper()
        summary = str(payload.get("summary", ""))
        if self._is_web():
            await self._agent_ui(
                "trading_result",
                payload,
                content=f"{decision}: {summary}" if summary else decision,
            )
        if self._bus is None or not self._channel or not self._chat_id:
            return
        if not include_card:
            return
        if self._channel == "telegram":
            from nanobot.channels.telegram.trading_cards import render_recommendation_card

            card = render_recommendation_card(payload)
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=card,
                    metadata={"parse_mode": "HTML"},
                )
            )
        elif self._channel == "whatsapp":
            from nanobot.channels.whatsapp.trading_cards import render_recommendation_card

            card = render_recommendation_card(payload)
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=card,
                )
            )

    def _is_web(self) -> bool:
        return self._channel in ("websocket", "")

    async def _agent_ui(
        self,
        kind: str,
        data: dict[str, Any],
        *,
        content: str,
    ) -> None:
        if self._bus is None or not self._channel or not self._chat_id:
            return
        await self._bus.publish_outbound(
            OutboundMessage(
                channel=self._channel,
                chat_id=self._chat_id,
                content=content,
                event=ProgressEvent(content=content),
                metadata={
                    OUTBOUND_META_AGENT_UI: {
                        "kind": kind,
                        "data": data,
                    }
                },
            )
        )

    async def _publish(self, event: StageEvent) -> None:
        if self._bus is None or not self._channel or not self._chat_id:
            return
        if self._is_web():
            await self._agent_ui(
                "trading_stage",
                event.to_wire(),
                content=stage_label(event.stage, "en"),
            )
            return
        if self._channel == "telegram":
            self._telegram_rows = apply_stage_event(self._telegram_rows, event)
            checklist = render_arabic_progress(self._telegram_rows)
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=checklist,
                    event=ProgressEvent(content=checklist),
                    metadata={TRADING_PROGRESS_META: True},
                )
            )
            return
        if self._channel == "whatsapp":
            if self._whatsapp_progress_sent:
                return
            self._whatsapp_progress_sent = True
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=_WHATSAPP_PROGRESS,
                    event=ProgressEvent(content=_WHATSAPP_PROGRESS),
                    metadata={TRADING_PROGRESS_META: True},
                )
            )
