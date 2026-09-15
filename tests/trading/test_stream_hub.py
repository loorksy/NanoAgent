import asyncio

import pytest

from nanobot.trading.stream_hub import TradingStreamHub


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
        "nanobot.trading.stream_hub.subscribe_symbol_ticks",
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
