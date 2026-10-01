"""Compact frozen evidence text for trading team subagents."""

from __future__ import annotations

import json

from mokli.trading.tool_errors import model_json
from mokli.trading.types import AgentMarketContext


def format_market_evidence(market: AgentMarketContext, *, max_candles: int = 40) -> str:
    candles = market.candles[-max_candles:]
    rows = [
        {
            "t": c.time_ms,
            "o": round(c.open, 2),
            "h": round(c.high, 2),
            "l": round(c.low, 2),
            "c": round(c.close, 2),
        }
        for c in candles
    ]
    payload = {
        "symbol": market.symbol,
        "interval": market.interval,
        "last_close": round(market.last_close, 2),
        "atr": round(market.atr, 4),
        "quote_mid": round(market.quote_mid or market.last_close, 2),
        "sync_ok": market.sync.ok,
        "candles": rows,
    }
    return model_json(payload)


def fit_evidence_text(evidence: str, *, limit: int = 12000) -> str:
    """Evidence the role model reads.

    A short document is unchanged. When a candle list would pass ``limit``, the
    oldest bars are dropped so the JSON still parses. A document that is not a
    candle payload is left intact rather than cut mid-string.
    """
    if len(evidence) <= limit:
        return evidence
    try:
        payload = json.loads(evidence)
    except json.JSONDecodeError:
        return evidence[:limit]
    if not isinstance(payload, dict):
        return evidence
    candles = payload.get("candles")
    if not isinstance(candles, list):
        return evidence
    kept = _newest_candles_that_fit(payload, candles, limit)
    return model_json({**payload, "candles": kept})


def _newest_candles_that_fit(
    payload: dict[str, object],
    candles: list[object],
    limit: int,
) -> list[object]:
    lo = 0
    hi = len(candles)
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = {**payload, "candles": candles[-mid:] if mid else []}
        if len(model_json(candidate)) <= limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return candles[-best:] if best else []


_CANDLE_ROLE_FILES = frozenset({
    "structure",
    "liquidity",
    "scenario",
})

# A named chart role (H1, H4, D1) loads that interval. A generic trend role
# does not: the lead candle list is a different timeframe.
_NAMED_CHART_INTERVALS: tuple[tuple[str, str], ...] = (
    ("h1", "1h"),
    ("1h", "1h"),
    ("h4", "4h"),
    ("4h", "4h"),
    ("d1", "1d"),
    ("1d", "1d"),
    ("daily", "1d"),
)


def named_chart_interval(role: str) -> str | None:
    """Interval written in the role label. ``Trend Analyst`` has none."""
    key = (role or "").lower()
    for needle, interval in _NAMED_CHART_INTERVALS:
        if needle in key:
            return interval
    return None


def compact_timeframe_window(market: AgentMarketContext) -> dict[str, object]:
    """High, low, and last close for one higher timeframe. Not the bar list."""
    candles = market.candles
    high = max((candle.high for candle in candles), default=None)
    low = min((candle.low for candle in candles), default=None)
    return {
        "interval": market.interval,
        "bars": len(candles),
        "last_close": round(market.last_close, 2),
        "atr": round(market.atr, 4),
        "window_high": None if high is None else round(high, 2),
        "window_low": None if low is None else round(low, 2),
    }


def trend_evidence(lead_evidence: str, windows: list[dict[str, object]]) -> str:
    """Lead quote plus higher-timeframe windows. The lead candle list stays out."""
    try:
        payload = json.loads(lead_evidence)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.pop("candles", None)
    payload["higher_timeframes"] = windows
    return model_json(payload)


def evidence_with_macro_drivers(evidence: str, briefing: str) -> str:
    """Scoped market JSON plus the macro-driver list. The candle array is not added."""
    try:
        payload = json.loads(evidence)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        drivers = json.loads(briefing)
    except json.JSONDecodeError:
        drivers = {}
    rows = drivers.get("macroDrivers") if isinstance(drivers, dict) else None
    payload["macroDrivers"] = rows if isinstance(rows, list) else []
    return model_json(payload)


def scope_market_evidence(evidence: str, role: str, system_prompt: str = "") -> str:
    """Price and candles for structure roles. Other roles get the quote, not the candle dump."""
    from mokli.trading.teams.role_prompts import resolve_role_file

    if resolve_role_file(role, system_prompt) in _CANDLE_ROLE_FILES:
        return evidence
    try:
        payload = json.loads(evidence)
    except json.JSONDecodeError:
        return evidence
    if not isinstance(payload, dict) or "candles" not in payload:
        return evidence
    scoped = {key: value for key, value in payload.items() if key != "candles"}
    return model_json(scoped)


def attach_risk_spread(evidence: str, market: AgentMarketContext) -> str:
    """Bid, ask, and spread for the risk role only.

    Gates have not run yet, so this does not add a gate verdict. A missing
    bid or ask leaves the quote unchanged rather than inventing a spread.
    """
    bid = market.quote_bid
    ask = market.quote_ask
    if bid is None or ask is None:
        return evidence
    try:
        payload = json.loads(evidence)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        return evidence
    from mokli.trading.policy import GOLD_POINT

    payload["quote_bid"] = round(float(bid), 2)
    payload["quote_ask"] = round(float(ask), 2)
    payload["spread_points"] = round(abs(float(ask) - float(bid)) / GOLD_POINT, 2)
    return model_json(payload)
