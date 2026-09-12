"""Publish trading stage events to WebUI (agent_ui) and Telegram (Arabic)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.bus.outbound_events import ProgressEvent
from nanobot.channels.telegram.trading_progress import (
    TelegramStageRow,
    apply_stage_event,
    render_arabic_progress,
)
from nanobot.trading.stage_events import StageEvent, stage_label

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus


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

    def sync_emit(self, event: StageEvent) -> None:
        """Sync callback for ``run_unified_chart_agent(emit=...)``."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._publish(event))
            return
        loop.create_task(self._publish(event))

    async def open_chart(self, interval: str = "15m") -> None:
        await self._agent_ui(
            "trading_chart_open",
            {"interval": interval, "symbol": "XAUUSD"},
            content="Opening gold chart…",
        )

    async def publish_result(self, payload: dict[str, Any]) -> None:
        decision = str(payload.get("decision", "wait")).upper()
        summary = str(payload.get("summary", ""))
        await self._agent_ui(
            "trading_result",
            payload,
            content=f"{decision}: {summary}" if summary else decision,
        )
        if self._bus is None or not self._channel or not self._chat_id:
            return
        if self._channel == "telegram":
            from nanobot.channels.telegram.trading_cards import render_recommendation_card

            card = render_recommendation_card(payload)
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=card,
                    event=ProgressEvent(content=card),
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
                    event=ProgressEvent(content=card),
                )
            )

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
        label = stage_label(event.stage, "en")
        await self._agent_ui(
            "trading_stage",
            event.to_wire(),
            content=label,
        )
        if self._channel in ("telegram", "whatsapp"):
            self._telegram_rows = apply_stage_event(self._telegram_rows, event)
            checklist = render_arabic_progress(self._telegram_rows)
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=checklist,
                    event=ProgressEvent(content=checklist),
                )
            )
