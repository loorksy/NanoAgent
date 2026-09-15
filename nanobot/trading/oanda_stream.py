"""Shared OANDA pricing stream — one upstream connection, many listeners."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from nanobot.trading.config import TradingConfig, load_trading_config
from nanobot.trading.gold import DATA_SYMBOL, OANDA_INSTRUMENT

TickListener = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class StreamTick:
    symbol: str
    bid: float
    ask: float
    mid: float
    time: int


_listeners: dict[str, set[TickListener]] = {}
_task: asyncio.Task[None] | None = None
_stop = False


def _stream_base_url(config: TradingConfig) -> str:
    if "fxtrade" in config.oanda_base_url:
        return "https://stream-fxtrade.oanda.com"
    return "https://stream-fxpractice.oanda.com"


def subscribe_symbol_ticks(symbol: str, listener: TickListener) -> Callable[[], None]:
    key = symbol.upper()
    bucket = _listeners.setdefault(key, set())
    bucket.add(listener)
    _ensure_running()
    def unsubscribe() -> None:
        bucket.discard(listener)
        if not bucket:
            _listeners.pop(key, None)
        if not any(_listeners.values()):
            _stop_stream()
    return unsubscribe


def _ensure_running() -> None:
    global _task, _stop
    if _task is not None and not _task.done():
        return
    _stop = False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_run_stream(), name="oanda-price-stream")


def _stop_stream() -> None:
    global _stop, _task
    _stop = True
    if _task is not None:
        _task.cancel()
        _task = None


def _dispatch(tick: StreamTick) -> None:
    payload = {
        "symbol": tick.symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "mid": tick.mid,
        "time": tick.time,
    }
    for listener in tuple(_listeners.get(tick.symbol, ())):
        try:
            listener(payload)
        except Exception:
            logger.debug("oanda tick listener failed", exc_info=True)


async def _run_stream() -> None:
    reconnect_delay = 1.0
    while not _stop and any(_listeners.values()):
        config = load_trading_config()
        if not config.oanda_configured or not config.oanda_account_id:
            await asyncio.sleep(2.0)
            continue
        url = (
            f"{_stream_base_url(config)}/v3/accounts/{config.oanda_account_id}"
            f"/pricing/stream?instruments={OANDA_INSTRUMENT}"
        )
        headers = {"Authorization": f"Bearer {config.oanda_api_token or ''}"}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f"OANDA stream HTTP {response.status_code}")
                    reconnect_delay = 1.0
                    buffer = ""
                    async for chunk in response.aiter_text():
                        if _stop or not any(_listeners.values()):
                            break
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                msg = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if msg.get("type") != "PRICE":
                                continue
                            bid = _num((msg.get("bids") or [{}])[0].get("price"))
                            ask = _num((msg.get("asks") or [{}])[0].get("price"))
                            if bid is None or ask is None:
                                continue
                            ts = _parse_time(msg.get("time")) or int(time.time() * 1000)
                            _dispatch(
                                StreamTick(
                                    symbol=DATA_SYMBOL,
                                    bid=bid,
                                    ask=ask,
                                    mid=(bid + ask) / 2,
                                    time=ts,
                                )
                            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("OANDA stream error: {}", exc)
        if _stop or not any(_listeners.values()):
            break
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 30.0)


def _parse_time(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    from datetime import datetime

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n == n else None
