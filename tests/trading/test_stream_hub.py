import asyncio
import threading
import time
from unittest.mock import MagicMock

import pytest

from mokli.trading.oanda import OandaQuote
from mokli.trading.stream_hub import TradingStreamHub


@pytest.mark.asyncio
async def test_stream_hub_broadcasts_oanda_tick(monkeypatch) -> None:
    hub = TradingStreamHub()
    events: list[dict] = []

    async def broadcaster(event: str, **fields) -> None:
        events.append({"event": event, **fields})

    tick_payload = {
        "symbol": "XAUUSD",
        "bid": 2650.1,
        "ask": 2650.3,
        "mid": 2650.2,
        "time": 1_700_000_000_000,
    }

    listeners: list = []

    def fake_subscribe(_symbol: str, listener):
        listeners.append(listener)
        listener(tick_payload)
        return lambda: None

    monkeypatch.setattr(
        "mokli.trading.stream_hub.subscribe_symbol_ticks",
        fake_subscribe,
    )

    hub.configure(broadcaster=broadcaster, has_listeners=lambda: True)
    await hub.start()
    await asyncio.sleep(0.05)
    await hub.stop()

    assert events
    assert events[0]["event"] == "trading_stream"
    assert events[0]["kind"] == "quote"
    assert events[0]["mid"] == 2650.2


@pytest.mark.asyncio
async def test_quote_fallback_leaves_the_event_loop_free(monkeypatch) -> None:
    """The quiet-stream poll reads the broker off the event loop."""
    hub = TradingStreamHub()
    order: list[str] = []

    def slow_quote(symbol: str, *, config: object | None = None) -> OandaQuote:
        del symbol, config
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        hub._running = False
        return OandaQuote(symbol="XAUUSD", bid=1.0, ask=1.2, mid=1.1, tradeable=True)

    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    monkeypatch.setattr(
        "mokli.trading.stream_hub.subscribe_symbol_ticks",
        lambda _symbol, _listener: (lambda: None),
    )
    monkeypatch.setattr(
        "mokli.trading.stream_hub.load_trading_config",
        lambda: MagicMock(oanda_configured=True),
    )
    monkeypatch.setattr("mokli.trading.stream_hub.fetch_quote", slow_quote)
    hub.configure(broadcaster=_noop_broadcast, has_listeners=lambda: True)
    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    await hub.start()
    for _ in range(20):
        if "worker" in order or "main" in order:
            break
        await asyncio.sleep(0.05)
    await pending
    await hub.stop()
    assert order[0] == "tick"
    assert "worker" in order
    assert time.perf_counter() - started < 0.35


async def _noop_broadcast(event: str, **fields: object) -> None:
    del event, fields
