"""Build agent market context from the connected account.

Historical candles and the live quote come from the operator's MT5 terminal
when that account is linked. OANDA remains only when it is not.
"""

from __future__ import annotations

import logging
from typing import Any

from mokli.trading.broker_market import broker_candles, broker_quote, run_sync
from mokli.trading.config import TradingConfig, load_trading_config
from mokli.trading.geometry.detectors import compute_atr
from mokli.trading.gold import DATA_SYMBOL, require_gold
from mokli.trading.oanda import OandaCandle, OandaQuote, fetch_candles, fetch_quote
from mokli.trading.types import AgentMarketContext, Candle, MarketSync

logger = logging.getLogger(__name__)

_MIN_BARS = 20


def _to_candle(row: OandaCandle) -> Candle:
    return Candle(
        time_ms=row.time_ms,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        complete=row.complete,
    )


def _bar_to_candle(row: dict[str, Any]) -> Candle | None:
    try:
        stamp = int(row["time"])
        open_ = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if min(open_, high, low, close) <= 0:
        return None
    millis = stamp if stamp > 10_000_000_000 else stamp * 1000
    volume = row.get("volume")
    try:
        size = float(volume) if volume is not None else None
    except (TypeError, ValueError):
        size = None
    return Candle(
        time_ms=millis,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=size,
        complete=bool(row.get("complete", True)),
    )


def _quote_from_view(symbol: str, view: dict[str, Any] | None) -> OandaQuote | None:
    if not isinstance(view, dict):
        return None
    try:
        bid = float(view["bid"]) if view.get("bid") is not None else None
        ask = float(view["ask"]) if view.get("ask") is not None else None
        mid = float(view["mid"]) if view.get("mid") is not None else None
    except (TypeError, ValueError):
        return None
    if bid is None or ask is None:
        return None
    if mid is None:
        mid = (bid + ask) / 2
    return OandaQuote(
        symbol=str(view.get("symbol") or symbol),
        bid=bid,
        ask=ask,
        mid=mid,
        tradeable=bool(view.get("tradeable", True)),
        quoted_at=None,
    )


def _from_broker(symbol: str, interval: str, limit: int) -> AgentMarketContext:
    candles: list[Candle] = []
    quote: OandaQuote | None = None
    try:
        payload = run_sync(broker_candles(symbol, interval, limit))
        rows = payload.get("candles") if isinstance(payload, dict) else None
        for row in rows or []:
            if isinstance(row, dict):
                candle = _bar_to_candle(row)
                if candle is not None:
                    candles.append(candle)
        quoted = run_sync(broker_quote(symbol))
        view = quoted.get("quote") if isinstance(quoted, dict) else None
        quote = _quote_from_view(symbol, view if isinstance(view, dict) else None)
    except Exception:
        logger.warning("MT5 analysis candles failed", exc_info=True)
        candles = []
        quote = None

    if len(candles) < _MIN_BARS:
        if candles:
            sync = MarketSync(ok=False, reason="Insufficient candle history", gapped=True)
        else:
            sync = MarketSync(ok=False, reason="MT5 candle history unavailable")
    else:
        sync = MarketSync(ok=True)

    last_close = candles[-1].close if candles else 0.0
    return AgentMarketContext(
        symbol=symbol,
        interval=interval,
        candles=candles,
        last_close=last_close,
        atr=compute_atr(candles),
        sync=sync,
        quote_mid=quote.mid if quote else None,
        quote_bid=quote.bid if quote else None,
        quote_ask=quote.ask if quote else None,
        tradeable=quote.tradeable if quote else False,
    )


def _from_oanda(
    symbol: str,
    interval: str,
    limit: int,
    config: TradingConfig,
) -> AgentMarketContext:
    candles_raw, _ = fetch_candles(symbol, interval, limit, config=config)
    candles = [_to_candle(c) for c in candles_raw]
    quote = fetch_quote(symbol, config=config)

    sync = MarketSync(ok=True)
    if not config.oanda_configured:
        sync = MarketSync(ok=False, reason="OANDA not configured")
    elif len(candles) < _MIN_BARS:
        sync = MarketSync(ok=False, reason="Insufficient candle history", gapped=True)

    last_close = candles[-1].close if candles else 0.0
    return AgentMarketContext(
        symbol=symbol,
        interval=interval,
        candles=candles,
        last_close=last_close,
        atr=compute_atr(candles),
        sync=sync,
        quote_mid=quote.mid if quote else None,
        quote_bid=quote.bid if quote else None,
        quote_ask=quote.ask if quote else None,
        tradeable=quote.tradeable if quote else False,
    )


def live_analysis_quote(symbol: str = DATA_SYMBOL) -> OandaQuote | None:
    """Bid/ask used by the recommendation gates. Same source as the candles."""
    require_gold(symbol)
    config = load_trading_config()
    if getattr(config, "mt5_configured", False) is True:
        try:
            quoted = run_sync(broker_quote(symbol))
        except Exception:
            logger.warning("MT5 analysis quote failed", exc_info=True)
            return None
        view = quoted.get("quote") if isinstance(quoted, dict) else None
        return _quote_from_view(symbol, view if isinstance(view, dict) else None)
    return fetch_quote(symbol, config=config)


def build_agent_market_context(
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    limit: int = 240,
) -> AgentMarketContext:
    require_gold(symbol)
    config = load_trading_config()
    if getattr(config, "mt5_configured", False) is True:
        return _from_broker(symbol, interval, limit)
    return _from_oanda(symbol, interval, limit, config)
