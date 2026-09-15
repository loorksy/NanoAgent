import asyncio

import pytest

from nanobot.trading.stream_hub import TradingStreamHub


@pytest.mark.asyncio
async def test_stream_hub_broadcasts_quote(monkeypatch) -> None:
    hub = TradingStreamHub()
    events: list[dict] = []

    async def broadcaster(event: str, **fields) -> None:
        events.append({"event": event, **fields})

    class _Quote:
        bid = 2650.1
        ask = 2650.3
        mid = 2650.2
        tradeable = True

    monkeypatch.setattr(
        "nanobot.trading.stream_hub.load_trading_config",
        lambda: type("Cfg", (), {"oanda_configured": True})(),
    )
    monkeypatch.setattr(
        "nanobot.trading.stream_hub.fetch_quote",
        lambda *_args, **_kwargs: _Quote(),
    )

    hub.configure(broadcaster=broadcaster, has_listeners=lambda: True)
    await hub.start()
    await asyncio.sleep(0.05)
    await hub.stop()

    assert events
    assert events[0]["event"] == "trading_stream"
    assert events[0]["kind"] == "quote"
    assert events[0]["mid"] == 2650.2
