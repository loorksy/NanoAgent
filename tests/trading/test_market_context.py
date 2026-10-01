"""Recommendation candles come from OANDA and the live quote from MetaAPI."""

from __future__ import annotations

from unittest.mock import MagicMock

from mokli.trading.market_context import build_agent_market_context, live_analysis_quote
from mokli.trading.oanda import OandaCandle, OandaQuote


def _candles(count: int = 22) -> list[OandaCandle]:
    return [
        OandaCandle(
            time_ms=1_700_000_000_000 + index * 900_000,
            open=1,
            high=2,
            low=1,
            close=1.5,
            volume=1,
            complete=True,
        )
        for index in range(count)
    ]


def test_analysis_reads_oanda_candles_and_metaapi_quote(monkeypatch) -> None:
    class Config:
        metaapi_configured = True
        oanda_configured = True

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (_candles(), False),
    )

    def _oanda_quote(*_args, **_kwargs):
        raise AssertionError("oanda quote")

    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", _oanda_quote)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_metaapi_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=4134.1, ask=4134.3, mid=4134.2, tradeable=True
        ),
    )

    context = build_agent_market_context("XAUUSD", "15m", limit=24)
    quote = live_analysis_quote("XAUUSD")

    assert context.sync.ok
    assert len(context.candles) == 22
    assert context.quote_bid == 4134.1
    assert context.quote_ask == 4134.3
    assert quote is not None
    assert abs((quote.mid or 0) - 4134.2) < 1e-6


def test_analysis_uses_oanda_quote_without_metaapi(monkeypatch) -> None:
    class Config:
        metaapi_configured = False
        oanda_configured = True

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (_candles(), False),
    )

    def _metaapi(*_args, **_kwargs):
        raise AssertionError("metaapi")

    monkeypatch.setattr("mokli.trading.market_context.fetch_metaapi_quote", _metaapi)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True
        ),
    )
    context = build_agent_market_context()
    assert context.sync.ok
    assert context.quote_mid == 1.5


def test_unconfigured_oanda_reports_the_candle_feed(monkeypatch) -> None:
    monkeypatch.setattr(
        "mokli.trading.market_context.load_trading_config",
        lambda: MagicMock(oanda_configured=False, spec=["oanda_configured"]),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: ([], False),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: None,
    )
    context = build_agent_market_context()
    assert context.sync.ok is False
    assert context.sync.reason == "OANDA not configured"


def test_same_turn_reuses_candles_and_refreshes_the_quote(monkeypatch) -> None:
    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    fetches = {"candles": 0}

    def _fetch(*_args, **_kwargs):
        fetches["candles"] += 1
        return _candles(), False

    quotes = iter(
        [
            OandaQuote(symbol="XAUUSD", bid=10, ask=11, mid=10.5, tradeable=True),
            OandaQuote(symbol="XAUUSD", bid=20, ask=21, mid=20.5, tradeable=True),
            OandaQuote(symbol="XAUUSD", bid=30, ask=31, mid=30.5, tradeable=True),
        ]
    )
    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", _fetch)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: next(quotes),
    )

    with turn_session_scope() as turn:
        first = build_agent_market_context("XAUUSD", "15m", limit=24)
        second = build_agent_market_context("XAUUSD", "15m", limit=24)
        other = build_agent_market_context("XAUUSD", "1h", limit=24)

    assert fetches["candles"] == 2
    assert turn.candle_reuses == 1
    assert first.quote_mid == 10.5
    assert second.quote_mid == 20.5
    assert [c.time_ms for c in second.candles] == [c.time_ms for c in first.candles]
    assert other.quote_mid == 30.5
    assert len(other.candles) == 22


def test_without_a_turn_each_call_fetches_candles(monkeypatch) -> None:
    class Config:
        metaapi_configured = False
        oanda_configured = True

    fetches = {"candles": 0}

    def _fetch(*_args, **_kwargs):
        fetches["candles"] += 1
        return _candles(), False

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", _fetch)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True
        ),
    )
    build_agent_market_context()
    build_agent_market_context()
    assert fetches["candles"] == 2


def test_overlapping_reads_of_one_window_fetch_once(monkeypatch) -> None:
    import contextvars
    import threading
    import time

    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    entered = {"n": 0}
    release = threading.Event()

    def _fetch(*_args, **_kwargs):
        entered["n"] += 1
        assert release.wait(timeout=1)
        return _candles(), False

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", _fetch)
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True
        ),
    )

    errors: list[BaseException] = []

    with turn_session_scope() as turn:
        contexts = [contextvars.copy_context() for _ in range(2)]

        def _run(ctx: contextvars.Context) -> None:
            try:
                ctx.run(build_agent_market_context, "XAUUSD", "15m", 24)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(ctx,)) for ctx in contexts]
        for thread in threads:
            thread.start()
        deadline = time.time() + 1
        while entered["n"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        assert entered["n"] == 1
        release.set()
        for thread in threads:
            thread.join(timeout=1)
            assert not thread.is_alive()

    assert errors == []
    assert entered["n"] == 1
    assert turn.candle_reuses == 1


def test_overlapping_quotes_share_the_download_then_the_next_reads_again(monkeypatch) -> None:
    import contextvars
    import threading
    import time

    from mokli.trading.market_context import resolve_live_quote
    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    entered = {"n": 0}
    release = threading.Event()

    def _fetch(*_args, **_kwargs):
        entered["n"] += 1
        assert release.wait(timeout=1)
        return OandaQuote(symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True)

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", _fetch)

    errors: list[BaseException] = []

    with turn_session_scope() as turn:
        contexts = [contextvars.copy_context() for _ in range(2)]

        def _run(ctx: contextvars.Context) -> None:
            try:
                ctx.run(resolve_live_quote, "XAUUSD")
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(ctx,)) for ctx in contexts]
        for thread in threads:
            thread.start()
        deadline = time.time() + 1
        while entered["n"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        assert entered["n"] == 1
        release.set()
        for thread in threads:
            thread.join(timeout=1)
            assert not thread.is_alive()
        assert errors == []
        assert turn.quote_reuses == 1

        quote, source = resolve_live_quote("XAUUSD")
        assert source == "oanda"
        assert quote is not None and quote.mid == 1.5
        assert entered["n"] == 2
        assert turn.quote_reuses == 1


def test_candles_and_quote_download_together(monkeypatch) -> None:
    """The two feeds do not wait on each other. A bar-only context still skips the quote."""
    import time

    class Config:
        metaapi_configured = False
        oanda_configured = True

    quote_calls = {"n": 0}

    def _slow_candles(*_args, **_kwargs):
        time.sleep(0.2)
        return _candles(), False

    def _slow_quote(*_args, **_kwargs):
        quote_calls["n"] += 1
        time.sleep(0.2)
        return OandaQuote(symbol="XAUUSD", bid=10, ask=11, mid=10.5, tradeable=True)

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr("mokli.trading.market_context.fetch_candles", _slow_candles)
    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", _slow_quote)

    started = time.perf_counter()
    context = build_agent_market_context("XAUUSD", "15m", limit=24)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    # Each feed sleeps 200ms. Sequential was their sum. Together stays near the slower one.
    print(f"MARKET_IO before_ms=400 after_ms={elapsed_ms}")
    assert context.sync.ok
    assert context.quote_mid == 10.5
    assert len(context.candles) == 22
    assert elapsed_ms < 350

    quote_calls["n"] = 0
    bars_only = build_agent_market_context("XAUUSD", "1h", limit=24, include_quote=False)
    assert bars_only.quote_mid is None
    assert quote_calls["n"] == 0


def test_overlapping_contexts_share_one_quote_download(monkeypatch) -> None:
    import contextvars
    import threading
    import time

    from mokli.trading.turn_session import turn_session_scope

    class Config:
        metaapi_configured = False
        oanda_configured = True

    entered = {"n": 0}
    release = threading.Event()

    def _quote(*_args, **_kwargs):
        entered["n"] += 1
        assert release.wait(timeout=1)
        return OandaQuote(symbol="XAUUSD", bid=1, ask=2, mid=1.5, tradeable=True)

    monkeypatch.setattr("mokli.trading.market_context.load_trading_config", lambda: Config())
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_candles",
        lambda *_args, **_kwargs: (_candles(), False),
    )
    monkeypatch.setattr("mokli.trading.market_context.fetch_quote", _quote)

    errors: list[BaseException] = []

    with turn_session_scope() as turn:
        contexts = [contextvars.copy_context() for _ in range(2)]

        def _run(ctx: contextvars.Context) -> None:
            try:
                ctx.run(build_agent_market_context, "XAUUSD", "15m", 24)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(ctx,)) for ctx in contexts]
        for thread in threads:
            thread.start()
        deadline = time.time() + 1
        while entered["n"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        assert entered["n"] == 1
        release.set()
        for thread in threads:
            thread.join(timeout=1)
            assert not thread.is_alive()

    assert errors == []
    assert entered["n"] == 1
    assert turn.quote_reuses == 1
