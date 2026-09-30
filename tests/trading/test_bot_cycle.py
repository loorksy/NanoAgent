"""The gold scan uses the quote already loaded with the candles."""

from mokli.trading.bots.coordinator import run_bot_cycle
from mokli.trading.types import AgentMarketContext, Candle, MarketSync


def test_bot_cycle_does_not_read_the_quote_again(monkeypatch) -> None:
    calls = {"market": 0, "direct": 0}
    candles = [Candle(index, 2300, 2320, 2290, 2315) for index in range(20)]

    def _market() -> AgentMarketContext:
        calls["market"] += 1
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=candles,
            last_close=2315.0,
            atr=8.0,
            sync=MarketSync(ok=True),
            quote_mid=2310.5,
        )

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr(
        "mokli.trading.bots.coordinator.build_agent_market_context",
        _market,
    )
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)

    outcome = run_bot_cycle(["multi_strategy"])

    assert calls == {"market": 1, "direct": 0}
    assert outcome.signals
    assert outcome.signals[0].price == 2310.5
