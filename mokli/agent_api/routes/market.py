"""Candles and quotes for the in-chat chart.

Candles come from OANDA. The live quote comes from MetaAPI when that
account is configured, and from OANDA otherwise.
"""

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


def _symbol_of(request: web.Request) -> str:
    return (request.query.get("symbol") or "XAUUSD").strip() or "XAUUSD"


def klines_payload(
    *,
    symbol: str,
    interval: str,
    limit: int,
    from_ms: int | None,
    to_ms: int | None,
    before_ms: int | None,
) -> dict[str, object]:
    from mokli.trading.config import load_trading_config
    from mokli.trading.gold import coerce_to_gold
    from mokli.trading.oanda import candle_to_wire, fetch_candles

    symbol = symbol.strip() or coerce_to_gold()
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


def quote_payload(symbol: str = "XAUUSD") -> dict[str, object]:
    from mokli.trading.config import load_trading_config
    from mokli.trading.gold import GoldOnlyError, coerce_to_gold
    from mokli.trading.market_context import resolve_live_quote
    from mokli.trading.metaapi_market import quote_time_seconds

    symbol = symbol.strip() or coerce_to_gold()
    config = load_trading_config()
    configured = bool(config.oanda_configured or getattr(config, "metaapi_configured", False) is True)
    if not configured:
        return {"symbol": symbol, "configured": False, "source": "oanda", "quote": None}
    try:
        quote, source = resolve_live_quote(symbol, config)
    except GoldOnlyError:
        return {"symbol": symbol, "configured": configured, "source": "oanda", "quote": None}
    if quote is None:
        return {"symbol": symbol, "configured": True, "source": source, "quote": None}
    tick: dict[str, object] = {
        "bid": quote.bid,
        "ask": quote.ask,
        "mid": quote.mid,
        "tradeable": quote.tradeable,
    }
    stamp = quote_time_seconds(quote.quoted_at)
    if stamp is not None:
        tick["time"] = stamp
    return {
        "symbol": quote.symbol,
        "configured": True,
        "source": source,
        "quote": tick,
    }


def symbols_payload(query: str, limit: int) -> dict[str, object]:
    text = query.casefold()
    row = {
        "name": "XAUUSD",
        "description": "Gold",
        "digits": 2,
        "path": "Metals",
    }
    matched = not text or text in "xauusd" or text in "gold" or "xau" in text or "ذهب" in text
    rows = [row] if matched else []
    return {
        "ok": True,
        "source": "oanda",
        "total": len(rows),
        "symbols": rows[:limit],
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
    symbol = _symbol_of(request)
    window = {
        "from_ms": _query_ms(request, "from"),
        "to_ms": _query_ms(request, "to"),
        "before_ms": _query_ms(request, "before"),
    }
    payload = await asyncio.to_thread(
        klines_payload,
        symbol=symbol,
        interval=interval,
        limit=limit,
        **window,
    )
    return ok(payload)


async def get_quote(request: web.Request) -> web.Response:
    require_scope(request, "read")
    symbol = _symbol_of(request)
    return ok(await asyncio.to_thread(quote_payload, symbol))


async def get_symbols(request: web.Request) -> web.Response:
    require_scope(request, "read")
    query = (request.query.get("q") or "").strip()
    raw_limit = request.query.get("limit")
    limit = 80
    if raw_limit is not None and raw_limit.strip():
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ApiError(400, "invalid_query", details={"param": "limit"}) from exc
    limit = min(max(limit, 1), 800)
    return ok(symbols_payload(query, limit))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/market/klines", get_klines)
    router.add_get(f"{prefix}/market/quote", get_quote)
    router.add_get(f"{prefix}/market/symbols", get_symbols)
