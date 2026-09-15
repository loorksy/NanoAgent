"""Broadcast live trading quotes and trace events to WebUI WebSocket clients."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from nanobot.trading.config import load_trading_config
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote

BroadcastFn = Callable[..., Awaitable[None]]
HasListenersFn = Callable[[], bool]

_QUOTE_INTERVAL_S = 1.5


class TradingStreamHub:
    def __init__(self) -> None:
        self._broadcast: BroadcastFn | None = None
        self._has_listeners: HasListenersFn | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def configure(
        self,
        *,
        broadcaster: BroadcastFn,
        has_listeners: HasListenersFn,
    ) -> None:
        self._broadcast = broadcaster
        self._has_listeners = has_listeners

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_quotes(), name="trading-stream-hub")

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def publish_trace(self, stage: dict[str, Any]) -> None:
        await self._emit(kind="trace", stage=stage)

    async def _emit(self, **fields: Any) -> None:
        if self._broadcast is None:
            return
        try:
            await self._broadcast("trading_stream", **fields)
        except Exception:
            logger.debug("trading stream broadcast failed", exc_info=True)

    async def _poll_quotes(self) -> None:
        while self._running:
            try:
                if self._has_listeners and not self._has_listeners():
                    await asyncio.sleep(_QUOTE_INTERVAL_S)
                    continue
                config = load_trading_config()
                if not config.oanda_configured:
                    await asyncio.sleep(_QUOTE_INTERVAL_S)
                    continue
                quote = fetch_quote(DATA_SYMBOL, config=config)
                if quote is None or quote.mid is None:
                    await asyncio.sleep(_QUOTE_INTERVAL_S)
                    continue
                await self._emit(
                    kind="quote",
                    symbol=DATA_SYMBOL,
                    bid=quote.bid,
                    ask=quote.ask,
                    mid=quote.mid,
                    tradeable=quote.tradeable,
                    ts=int(time.time() * 1000),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("trading quote poll failed", exc_info=True)
            await asyncio.sleep(_QUOTE_INTERVAL_S)


_hub: TradingStreamHub | None = None


def get_trading_stream_hub() -> TradingStreamHub:
    global _hub
    if _hub is None:
        _hub = TradingStreamHub()
    return _hub
