"""Gold candles and quote for the in-chat chart."""

from __future__ import annotations

import asyncio

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.errors import ApiError
from mokli.agent_api.routes._util import ok


def _query_ms(request: web.Request, name: str) -> int | None:
    raw = request.query.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ApiError(400, "invalid_query", details={"param": name}) from exc


def klines_payload(
    *,
    interval: str,
    limit: int,
    from_ms: int | None,
    to_ms: int | None,
    before_ms: int | None,
) -> dict[str, object]:
    from mokli.trading.config import load_trading_config
    from mokli.trading.gold import coerce_to_gold
    from mokli.trading.oanda import candle_to_wire, fetch_candles

    symbol = coerce_to_gold()
    config = load_trading_config()
    if not config.oanda_configured:
        return {
            "symbol": symbol,
            "interval": interval,
            "source": "oanda",
            "configured": False,
            "candles": [],
            "hasMore": False,
        }
    candles, has_more = fetch_candles(
        symbol,
        interval,
        limit,
        before_ms=before_ms,
        from_ms=from_ms,
        to_ms=to_ms,
        config=config,
    )
    return {
        "symbol": symbol,
        "interval": interval,
        "source": "oanda",
        "configured": True,
        "candles": [candle_to_wire(candle) for candle in candles],
        "hasMore": has_more,
    }


def quote_payload() -> dict[str, object]:
    from mokli.trading.config import load_trading_config
    from mokli.trading.gold import coerce_to_gold
    from mokli.trading.oanda import fetch_quote

    symbol = coerce_to_gold()
    config = load_trading_config()
    if not config.oanda_configured:
        return {"symbol": symbol, "configured": False, "quote": None}
    quote = fetch_quote(symbol, config=config)
    if quote is None:
        return {"symbol": symbol, "configured": True, "quote": None}
    return {
        "symbol": symbol,
        "configured": True,
        "quote": {
            "bid": quote.bid,
            "ask": quote.ask,
            "mid": quote.mid,
            "tradeable": quote.tradeable,
        },
    }


async def get_klines(request: web.Request) -> web.Response:
    require_scope(request, "read")
    interval = (request.query.get("interval") or "15m").strip() or "15m"
    raw_limit = request.query.get("limit")
    limit = 300
    if raw_limit is not None and raw_limit.strip():
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ApiError(400, "invalid_query", details={"param": "limit"}) from exc
    limit = min(max(limit, 1), 5000)
    payload = await asyncio.to_thread(
        klines_payload,
        interval=interval,
        limit=limit,
        from_ms=_query_ms(request, "from"),
        to_ms=_query_ms(request, "to"),
        before_ms=_query_ms(request, "before"),
    )
    return ok(payload)


async def get_quote(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok(await asyncio.to_thread(quote_payload))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/market/klines", get_klines)
    router.add_get(f"{prefix}/market/quote", get_quote)
