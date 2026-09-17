"""FEATURE-01 — Telegram MTProto headline listener (Telethon, optional extra)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from nanobot.trading.intel.optional_deps import module_available

HeadlineHandler = Callable[[str, str], Awaitable[None] | None]


@dataclass(frozen=True)
class TelegramHeadline:
    channel: str
    text: str
    message_id: int


class TelegramHeadlineSource:
    """Subscribe to public news channels. Requires `telethon` extra and API credentials."""

    def __init__(
        self,
        *,
        api_id: int | None = None,
        api_hash: str | None = None,
        session: str = "lonora-news",
        channels: list[str] | None = None,
    ) -> None:
        self.api_id = api_id or int(os.environ.get("TELEGRAM_API_ID", "0") or 0)
        self.api_hash = api_hash or os.environ.get("TELEGRAM_API_HASH", "")
        self.session = session
        self.channels = channels or [
            "financialjuice",
            "walterbloomberg",
        ]
        self._client: Any = None

    def configured(self) -> bool:
        return bool(self.api_id and self.api_hash)

    def sdk_installed(self) -> bool:
        return module_available("telethon")

    def available(self) -> bool:
        return self.sdk_installed() and self.configured()

    def backend(self) -> str:
        if self.available():
            return "telethon"
        if not self.sdk_installed():
            return "unavailable_sdk"
        return "unavailable_credentials"

    async def fetch_recent(self, *, limit: int = 8) -> list[TelegramHeadline]:
        """Pull recent channel messages when Telethon + credentials are present.

        This is a finite fetch for intel scans. Live listen() remains long-running
        and is not started from the scan tool.
        """
        if not self.available():
            return []
        from telethon import TelegramClient

        client = TelegramClient(self.session, self.api_id, self.api_hash)
        await client.start()
        rows: list[TelegramHeadline] = []
        try:
            for channel in self.channels:
                entity = await client.get_entity(channel)
                async for message in client.iter_messages(entity, limit=max(1, limit)):
                    text = str(getattr(message, "message", "") or "")
                    if not text.strip():
                        continue
                    rows.append(
                        TelegramHeadline(
                            channel=channel,
                            text=text,
                            message_id=int(getattr(message, "id", 0) or 0),
                        )
                    )
                    if len(rows) >= limit:
                        break
                if len(rows) >= limit:
                    break
        finally:
            await client.disconnect()
        return rows[:limit]

    async def listen(self, handler: HeadlineHandler) -> None:
        if not self.available():
            raise RuntimeError("Telethon extra or TELEGRAM_API_ID/HASH is missing")
        from telethon import TelegramClient, events

        self._client = TelegramClient(self.session, self.api_id, self.api_hash)
        await self._client.start()

        @self._client.on(events.NewMessage(chats=self.channels))
        async def _on_new(event: Any) -> None:
            text = str(getattr(event, "raw_text", "") or "")
            chat = getattr(getattr(event, "chat", None), "username", "") or "telegram"
            result = handler(chat, text)
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]

        await self._client.run_until_disconnected()
