"""Build agent market context from OANDA candles and the live quote.

Candles come from OANDA. The live bid/ask comes from MetaAPI when that
account is configured, and from OANDA otherwise.
"""

from __future__ import annotations

import logging

from mokli.trading.config import TradingConfig, load_trading_config
from mokli.trading.geometry.detectors import compute_atr
from mokli.trading.gold import DATA_SYMBOL, require_gold
from mokli.trading.metaapi_market import fetch_metaapi_quote
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


def resolve_live_quote(
    symbol: str = DATA_SYMBOL,
    config: TradingConfig | None = None,
) -> tuple[OandaQuote | None, str]:
    """Live gold quote and the feed that produced it.

    Overlapping reads in one turn share the download already in progress.
    A later read, after that download finishes, fetches again.
    """
    require_gold(symbol)
    config = config or load_trading_config()

    def _fetch() -> tuple[OandaQuote | None, str]:
        if getattr(config, "metaapi_configured", False) is True:
            try:
                quote = fetch_metaapi_quote(symbol, config=config)
            except Exception:
                logger.warning("MetaAPI analysis quote failed")
                quote = None
            if quote is not None:
                return quote, "metaapi"
        return fetch_quote(symbol, config=config), "oanda"

    from mokli.trading.turn_session import current_turn_session

    turn = current_turn_session()
    if turn is None:
        return _fetch()
    return turn.share_inflight(
        ("quote", symbol),
        _fetch,
        on_reuse=lambda: setattr(turn, "quote_reuses", turn.quote_reuses + 1),
    )


def live_analysis_quote(symbol: str = DATA_SYMBOL) -> OandaQuote | None:
    """Bid/ask used by the recommendation gates."""
    quote, _source = resolve_live_quote(symbol)
    return quote


def build_agent_market_context(
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    limit: int = 240,
    *,
    include_quote: bool = True,
) -> AgentMarketContext:
    require_gold(symbol)
    config = load_trading_config()
    from mokli.trading.turn_session import current_turn_session

    turn = current_turn_session()

    def _fetch_rows() -> list[Candle]:
        candles_raw, _ = fetch_candles(symbol, interval, limit, config=config)
        return [_to_candle(row) for row in candles_raw]

    if turn is None:
        candles = _fetch_rows()
    else:
        candles = turn.load_candles(symbol, interval, limit, _fetch_rows)
    # Callers that only need bars (a higher-timeframe bias, a trend window)
    # must not download a quote they discard. Gates still read a fresh quote.
    quote = None
    if include_quote:
        quote, _source = resolve_live_quote(symbol, config)

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
