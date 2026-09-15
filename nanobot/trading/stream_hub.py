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
from nanobot.trading.oanda_stream import subscribe_symbol_ticks

BroadcastFn = Callable[..., Awaitable[None]]
HasListenersFn = Callable[[], bool]

_QUOTE_FALLBACK_INTERVAL_S = 5.0


class TradingStreamHub:
    def __init__(self) -> None:
        self._broadcast: BroadcastFn | None = None
        self._has_listeners: HasListenersFn | None = None
        self._fallback_task: asyncio.Task[None] | None = None
        self._unsubscribe_ticks: Callable[[], None] | None = None
        self._running = False
        self._last_stream_tick_at = 0.0

    def configure(
        self,
        *,
        broadcaster: BroadcastFn,
        has_listeners: HasListenersFn,
    ) -> None:
        self._broadcast = broadcaster
        self._has_listeners = has_listeners

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        def on_tick(tick: dict[str, Any]) -> None:
            self._last_stream_tick_at = time.monotonic()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            loop.create_task(self._emit(kind="quote", **tick))

        self._unsubscribe_ticks = subscribe_symbol_ticks(DATA_SYMBOL, on_tick)
        self._fallback_task = asyncio.create_task(
            self._quote_fallback(),
            name="trading-stream-fallback",
        )

    async def stop(self) -> None:
        self._running = False
        if self._unsubscribe_ticks is not None:
            self._unsubscribe_ticks()
            self._unsubscribe_ticks = None
        if self._fallback_task is not None:
            self._fallback_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._fallback_task
            self._fallback_task = None

    async def publish_trace(self, stage: dict[str, Any]) -> None:
        await self._emit(kind="trace", stage=stage)

    async def _emit(self, **fields: Any) -> None:
        if self._broadcast is None:
            return
        if self._has_listeners and not self._has_listeners():
            return
        try:
            await self._broadcast("trading_stream", **fields)
        except Exception:
            logger.debug("trading stream broadcast failed", exc_info=True)

    async def _quote_fallback(self) -> None:
        """HTTP quote poll when OANDA stream is quiet or unconfigured."""
        while self._running:
            try:
                if self._has_listeners and not self._has_listeners():
                    await asyncio.sleep(_QUOTE_FALLBACK_INTERVAL_S)
                    continue
                if time.monotonic() - self._last_stream_tick_at < _QUOTE_FALLBACK_INTERVAL_S:
                    await asyncio.sleep(_QUOTE_FALLBACK_INTERVAL_S)
                    continue
                config = load_trading_config()
                if not config.oanda_configured:
                    await asyncio.sleep(_QUOTE_FALLBACK_INTERVAL_S)
                    continue
                quote = fetch_quote(DATA_SYMBOL, config=config)
                if quote is None or quote.mid is None:
                    await asyncio.sleep(_QUOTE_FALLBACK_INTERVAL_S)
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
                logger.debug("trading quote fallback failed", exc_info=True)
            await asyncio.sleep(_QUOTE_FALLBACK_INTERVAL_S)


_hub: TradingStreamHub | None = None


def get_trading_stream_hub() -> TradingStreamHub:
    global _hub
    if _hub is None:
        _hub = TradingStreamHub()
    return _hub
