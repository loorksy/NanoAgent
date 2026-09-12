"""Build agent market context from OANDA candles."""

from __future__ import annotations

from nanobot.trading.config import load_trading_config
from nanobot.trading.geometry.detectors import compute_atr
from nanobot.trading.gold import DATA_SYMBOL, require_gold
from nanobot.trading.oanda import OandaCandle, fetch_candles, fetch_quote
from nanobot.trading.types import AgentMarketContext, Candle, MarketSync


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


def build_agent_market_context(
    symbol: str = DATA_SYMBOL,
    interval: str = "15m",
    limit: int = 240,
) -> AgentMarketContext:
    require_gold(symbol)
    config = load_trading_config()
    candles_raw, _ = fetch_candles(symbol, interval, limit, config=config)
    candles = [_to_candle(c) for c in candles_raw]
    quote = fetch_quote(symbol, config=config)

    sync = MarketSync(ok=True)
    if not config.oanda_configured:
        sync = MarketSync(ok=False, reason="OANDA not configured")
    elif len(candles) < 20:
        sync = MarketSync(ok=False, reason="Insufficient candle history", gapped=True)

    last_close = candles[-1].close if candles else 0.0
    atr = compute_atr(candles)

    return AgentMarketContext(
        symbol=symbol,
        interval=interval,
        candles=candles,
        last_close=last_close,
        atr=atr,
        sync=sync,
        quote_mid=quote.mid if quote else None,
    )
