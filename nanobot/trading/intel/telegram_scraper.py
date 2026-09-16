"""FEATURE-01 — Telegram MTProto headline listener (Telethon, optional extra)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

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

    def available(self) -> bool:
        try:
            import telethon  # noqa: F401
        except ImportError:
            return False
        return self.configured()

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
