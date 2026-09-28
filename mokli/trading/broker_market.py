"""Live prices and candles from the operator's connected MT5 account.

Charts and the agent read this module. The terminal's tick is the price;
candles are the terminal's rates. An external feed is used only when no
MT5 account is configured.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from mokli.trading.mt5_broker import get_transport

_CHART_INTERVALS = {
    "1m": "M1",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "4h": "H4",
    "1d": "D1",
    "d": "D1",
    "1w": "W1",
}
_BAR_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "d": 86400,
    "1w": 604800,
}


def chart_timeframe(interval: str) -> str:
    key = (interval or "15m").strip().lower()
    return _CHART_INTERVALS.get(key, "M15")


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def quote_view(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Public bid/ask from a transport quote envelope. Drops connection errors."""
    if not isinstance(payload, dict) or not payload.get("ok"):
        return None
    price = payload.get("quote") if isinstance(payload.get("quote"), dict) else payload
    bid = _num(price.get("bid"))
    ask = _num(price.get("ask"))
    if bid is None or ask is None:
        return None
    mid = (bid + ask) / 2
    spread = _num(price.get("spread"))
    if spread is None:
        spread = ask - bid
    when = price.get("time")
    try:
        stamp = int(when) if when is not None else None
    except (TypeError, ValueError):
        stamp = None
    return {
        "symbol": str(price.get("symbol") or ""),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "time": stamp,
        "tradeable": True,
        "source": "mt5",
    }


def candles_from_rates(
    rows: list[dict[str, Any]],
    *,
    from_ms: int | None = None,
    to_ms: int | None = None,
    before_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Chart bars from terminal rates. ``time`` is unix seconds, oldest first."""
    candles: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stamp = _num(row.get("time"))
        open_ = _num(row.get("open"))
        high = _num(row.get("high"))
        low = _num(row.get("low"))
        close = _num(row.get("close"))
        if None in {stamp, open_, high, low, close}:
            continue
        volume = _num(row.get("tick_volume"))
        if volume is None:
            volume = _num(row.get("real_volume")) or 0.0
        seconds = int(stamp or 0)
        millis = seconds * 1000
        if from_ms is not None and millis < from_ms:
            continue
        if to_ms is not None and millis > to_ms:
            continue
        if before_ms is not None and millis >= before_ms:
            continue
        candles.append(
            {
                "time": seconds,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "complete": True,
            }
        )
    candles.sort(key=lambda item: int(item["time"]))
    if candles:
        candles[-1]["complete"] = False
    return candles


def bar_count(interval: str, limit: int, from_ms: int | None, to_ms: int | None) -> int:
    """How many terminal bars to request.

    The terminal returns the newest bars. A chart asking for an older window
    still needs every bar from that window up to now, otherwise the filter
    drops the series and history stops.
    """
    count = max(1, min(int(limit), 5000))
    bar = _BAR_SECONDS.get((interval or "").strip().lower(), 900)
    now_ms = int(time.time() * 1000)
    if from_ms is not None and from_ms < now_ms:
        depth = int((now_ms - from_ms) / 1000 / bar) + 8
        return max(count, min(depth, 5000))
    if from_ms is not None and to_ms is not None and to_ms > from_ms:
        span = int((to_ms - from_ms) / 1000 / bar) + 5
        return max(count, min(span, 5000))
    return count


def run_sync(coro: Any) -> Any:
    """Run a broker coroutine from the synchronous analysis path."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    outcome: dict[str, Any] = {}

    def _runner() -> None:
        try:
            outcome["value"] = asyncio.run(coro)
        except Exception as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


async def broker_symbols(query: str = "", limit: int = 200) -> dict[str, Any]:
    transport = get_transport()
    payload = await transport.list_symbols(query, limit)
    if not isinstance(payload, dict):
        return {"ok": False, "source": "mt5", "symbols": [], "total": 0}
    payload.setdefault("source", "mt5")
    return payload


async def broker_quote(symbol: str) -> dict[str, Any]:
    name = symbol.strip()
    transport = get_transport()
    raw = await transport.quote(name)
    view = quote_view(raw if isinstance(raw, dict) else None)
    if view is None:
        error = raw.get("error") if isinstance(raw, dict) else None
        return {
            "ok": False,
            "symbol": name,
            "source": "mt5",
            "quote": None,
            "error": error,
        }
    if not view["symbol"]:
        view["symbol"] = name
    return {"ok": True, "symbol": view["symbol"], "source": "mt5", "quote": view}


async def broker_candles(
    symbol: str,
    interval: str,
    limit: int,
    *,
    from_ms: int | None = None,
    to_ms: int | None = None,
    before_ms: int | None = None,
) -> dict[str, Any]:
    name = symbol.strip()
    timeframe = chart_timeframe(interval)
    count = bar_count(interval, limit, from_ms, to_ms)
    transport = get_transport()
    rows = await transport.candles(name, timeframe, count)
    candles = candles_from_rates(
        list(rows or []),
        from_ms=from_ms,
        to_ms=to_ms,
        before_ms=before_ms,
    )
    return {
        "ok": bool(candles),
        "symbol": name,
        "interval": interval,
        "source": "mt5",
        "configured": True,
        "candles": candles,
        "hasMore": len(candles) >= min(limit, count),
    }
