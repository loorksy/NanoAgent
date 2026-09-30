"""The ATR replay loads bars itself and does not ask the model to paste them."""

from __future__ import annotations

import asyncio
import json
import time

from mokli.agent.tools.fast_backtest import FastBacktestTool
from mokli.trading.backtest.engine import replay
from mokli.trading.types import AgentMarketContext, Candle, MarketSync
from mokli.utils.helpers import estimate_prompt_tokens


def _rising(count: int = 80) -> list[Candle]:
    rows: list[Candle] = []
    price = 2300.0
    for index in range(count):
        price += 1.2
        rows.append(
            Candle(
                time_ms=index * 60_000,
                open=price - 0.2,
                high=price + 0.3,
                low=price - 0.4,
                close=price,
                volume=10,
            )
        )
    return rows


def _ohlc_json(candles: list[Candle]) -> str:
    return json.dumps(
        [
            {
                "time_ms": candle.time_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            }
            for candle in candles
        ]
    )


def test_backtest_tool_loads_bars_instead_of_reading_a_pasted_list(monkeypatch) -> None:
    calls = {"loads": 0, "quotes": 0, "warehouse": 0}

    def _market(*_args: object, **kwargs: object) -> AgentMarketContext:
        calls["loads"] += 1
        assert kwargs.get("include_quote") is False
        time.sleep(0.2)
        candles = _rising(200)
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=candles,
            last_close=candles[-1].close,
            atr=1.0,
            sync=MarketSync(ok=True),
        )

    def _quote(*_args: object, **_kwargs: object) -> None:
        calls["quotes"] += 1
        raise AssertionError("quote fetched")

    def _warehouse(*_args: object, **_kwargs: object) -> list[Candle]:
        calls["warehouse"] += 1
        return []

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _quote)
    monkeypatch.setattr("mokli.agent.tools.fast_backtest._load_warehouse", _warehouse)
    pasted = _ohlc_json(_rising(200))
    full = replay(_rising(200))
    before = estimate_prompt_tokens(
        [
            {"role": "user", "content": pasted},
            {"role": "tool", "content": json.dumps(full)},
        ]
    )
    started = time.perf_counter()
    raw = asyncio.run(FastBacktestTool().execute())
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    after = estimate_prompt_tokens([{"role": "tool", "content": raw}])
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["strategy"] == "atr_breakout"
    assert payload["trades"] > 0
    assert calls == {"loads": 1, "quotes": 0, "warehouse": 0}
    assert "time_ms" not in raw
    assert '"rs"' not in raw
    assert elapsed_ms < 350
    print(f"FAST_BACKTEST before_tokens={before} after_tokens={after}")


def test_pasted_bars_do_not_start_a_download(monkeypatch) -> None:
    def _market(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("market loaded")

    monkeypatch.setattr("mokli.agent.tools.fast_backtest._load_market_bars", _market)
    raw = asyncio.run(
        FastBacktestTool().execute(candles_json=_ohlc_json(_rising(80)))
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["candles"] == 80
    assert '"rs"' not in raw


def test_missing_feed_does_not_invent_prices(monkeypatch) -> None:
    def _market(*_args: object, **_kwargs: object) -> AgentMarketContext:
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=[],
            last_close=0.0,
            atr=0.0,
            sync=MarketSync(ok=False, reason="OANDA not configured"),
        )

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr("mokli.agent.tools.fast_backtest._load_warehouse", lambda *_a, **_k: [])
    raw = asyncio.run(FastBacktestTool().execute())
    payload = json.loads(raw)
    assert payload["reason_key"] == "trading.market_feed_unconfigured"
    assert payload["trades"] == 0
    assert "pnl" not in payload


def test_lab_loads_market_bars_when_the_request_has_none(monkeypatch) -> None:
    from mokli.trading.strategy_lab import lab_replay

    calls = {"loads": 0}

    def _market(*_args: object, **kwargs: object) -> AgentMarketContext:
        calls["loads"] += 1
        assert kwargs.get("include_quote") is False
        time.sleep(0.2)
        candles = _rising(80)
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=candles,
            last_close=candles[-1].close,
            atr=1.0,
            sync=MarketSync(ok=True),
        )

    def _warehouse(*_args: object, **_kwargs: object) -> list[Candle]:
        raise AssertionError("warehouse")

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr("mokli.trading.strategy_lab.load_warehouse_bars", _warehouse)
    started = time.perf_counter()
    payload = lab_replay("atr_breakout", [])
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    assert calls["loads"] == 1
    assert payload["status"] == "proposed"
    assert payload["executed"] is False
    assert payload["broker_order"] is False
    validation = payload["validation"]
    assert isinstance(validation, dict)
    assert "walk_forward" in validation
    assert elapsed_ms < 350
    print(f"LAB_REPLAY loads=1 elapsed_ms={elapsed_ms}")


def test_lab_does_not_invent_prices_when_the_feed_is_down(monkeypatch) -> None:
    from mokli.trading.strategy_lab import lab_replay

    def _market(*_args: object, **_kwargs: object) -> AgentMarketContext:
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=[],
            last_close=0.0,
            atr=0.0,
            sync=MarketSync(ok=False, reason="OANDA not configured"),
        )

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr("mokli.trading.strategy_lab.load_warehouse_bars", lambda *_a, **_k: [])
    payload = lab_replay("atr_breakout")
    assert payload["reason_key"] == "trading.market_feed_unconfigured"
    assert payload["trades"] == 0
    assert payload["broker_order"] is False
    assert "validation" not in payload


def test_warehouse_is_used_only_when_the_feed_is_empty(monkeypatch) -> None:
    def _market(*_args: object, **_kwargs: object) -> AgentMarketContext:
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            candles=[],
            last_close=0.0,
            atr=0.0,
            sync=MarketSync(ok=False, reason="OANDA not configured"),
        )

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr(
        "mokli.agent.tools.fast_backtest._load_warehouse",
        lambda *_a, **_k: _rising(80),
    )
    payload = json.loads(asyncio.run(FastBacktestTool().execute()))
    assert payload["ok"] is True
    assert payload["candles"] == 80
