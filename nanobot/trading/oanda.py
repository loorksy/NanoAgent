"""OANDA v20 read-only market data for gold."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from nanobot.trading.config import TradingConfig, load_trading_config
from nanobot.trading.gold import OANDA_INSTRUMENT, DATA_SYMBOL, require_gold

GRANULARITY: dict[str, str] = {
    "1m": "M1",
    "3m": "M3",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "2h": "H2",
    "4h": "H4",
    "6h": "H6",
    "8h": "H8",
    "12h": "H12",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}

BAR_DURATION_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
}

HISTORY_LOOKBACK_MS = int(10 * 365.25 * 24 * 60 * 60 * 1000)


@dataclass(frozen=True)
class OandaCandle:
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    complete: bool


@dataclass(frozen=True)
class OandaQuote:
    symbol: str
    bid: float | None
    ask: float | None
    mid: float | None
    tradeable: bool


def to_oanda_granularity(interval: str) -> str | None:
    return GRANULARITY.get(interval)


def bar_duration_ms(interval: str) -> int:
    return BAR_DURATION_MS.get(interval, 60_000)


def _auth_headers(config: TradingConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.oanda_api_token or ''}",
        "Content-Type": "application/json",
    }


def fetch_candles(
    symbol: str,
    interval: str,
    count: int,
    *,
    before_ms: int | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
    config: TradingConfig | None = None,
) -> tuple[list[OandaCandle], bool]:
    """Return candles and whether more history may exist."""
    config = config or load_trading_config()
    if not config.oanda_configured:
        return [], False

    require_gold(symbol)
    granularity = to_oanda_granularity(interval)
    if granularity is None:
        return [], False

    n = min(max(1, count), 5000)
    base = (
        f"{config.oanda_base_url}/v3/instruments/{OANDA_INSTRUMENT}/candles"
    )

    if from_ms is not None and to_ms is not None and to_ms > from_ms:
        bar_ms = bar_duration_ms(interval)
        clamped_to = min(to_ms, int(time.time() * 1000) - 1000)
        clamped_from = max(from_ms, clamped_to - 4800 * bar_ms)
        url = (
            f"{base}?granularity={granularity}"
            f"&from={_iso(clamped_from)}&to={_iso(clamped_to)}&price=M"
        )
    elif before_ms is not None and before_ms > 0:
        url = (
            f"{base}?granularity={granularity}&count={n}"
            f"&to={_iso(before_ms)}&price=M"
        )
    else:
        url = f"{base}?granularity={granularity}&count={n}&price=M"

    with httpx.Client(timeout=20.0) as client:
        response = client.get(url, headers=_auth_headers(config))
        response.raise_for_status()
        data = response.json()

    rows = data.get("candles") or []
    out: list[OandaCandle] = []
    for row in rows:
        mid = row.get("mid") or {}
        if not mid:
            continue
        t = _parse_time(row.get("time"))
        open_ = _num(mid.get("o"))
        high = _num(mid.get("h"))
        low = _num(mid.get("l"))
        close = _num(mid.get("c"))
        if t is None or None in (open_, high, low, close):
            continue
        out.append(
            OandaCandle(
                time_ms=t,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=_num(row.get("volume")),
                complete=row.get("complete") is True,
            )
        )
    out.sort(key=lambda c: c.time_ms)

    has_more = False
    if from_ms is not None and to_ms is not None:
        oldest = out[0].time_ms if out else 0
        has_more = bool(out) and oldest > int(time.time() * 1000) - HISTORY_LOOKBACK_MS + bar_duration_ms(interval)
    elif before_ms is not None and before_ms > 0:
        oldest = out[0].time_ms if out else 0
        has_more = bool(out) and oldest > int(time.time() * 1000) - HISTORY_LOOKBACK_MS + bar_duration_ms(interval)
    else:
        has_more = len(out) >= n
    return out, has_more


def fetch_quote(
    symbol: str,
    *,
    config: TradingConfig | None = None,
) -> OandaQuote | None:
    config = config or load_trading_config()
    if not config.oanda_configured or not config.oanda_account_id:
        return None
    require_gold(symbol)

    url = (
        f"{config.oanda_base_url}/v3/accounts/{config.oanda_account_id}/pricing"
        f"?instruments={OANDA_INSTRUMENT}"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=_auth_headers(config))
        response.raise_for_status()
        data = response.json()

    prices = data.get("prices") or []
    if not prices:
        return None
    row = prices[0]
    bid = _num((row.get("bids") or [{}])[0].get("price"))
    ask = _num((row.get("asks") or [{}])[0].get("price"))
    mid = None
    if bid is not None and ask is not None:
        mid = (bid + ask) / 2
    elif bid is not None or ask is not None:
        mid = bid if bid is not None else ask
    return OandaQuote(
        symbol=DATA_SYMBOL,
        bid=bid,
        ask=ask,
        mid=mid,
        tradeable=row.get("tradeable") is not False,
    )


def candle_to_wire(candle: OandaCandle) -> dict[str, Any]:
    return {
        "time": candle.time_ms // 1000,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "complete": candle.complete,
    }


def _iso(ms: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    from datetime import datetime

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n == n else None  # NaN guard
