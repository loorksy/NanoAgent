"""FEATURE-10 — free intermarket engine (yfinance first, MetaTrader5 symbols if present)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nanobot.trading.intel.optional_deps import module_available

SYMBOLS = {
    "dxy": ("DX-Y.NYB", "USDX", "DXY"),
    "xag": ("XAGUSD=X", "XAGUSD"),
    "oil": ("CL=F", "USOIL", "UKOIL"),
    "us10y": ("^TNX", "US10Y"),
    "xau": ("GC=F", "XAUUSD"),
}


@dataclass(frozen=True)
class IntermarketSnapshot:
    prices: dict[str, float]
    notes: list[str]
    source: str


def _yfinance_last(ticker: str) -> float | None:
    if not module_available("yfinance"):
        return None
    import yfinance as yf

    try:
        hist = yf.Ticker(ticker).history(period="2d", interval="5m")
    except Exception:
        return None
    if hist is None or hist.empty:
        return None
    close = hist["Close"].iloc[-1]
    return float(close)


def _mt5_last(symbol: str) -> float | None:
    if not module_available("MetaTrader5"):
        return None
    import MetaTrader5 as mt5  # noqa: N813

    try:
        if not mt5.initialize():
            return None
        info = mt5.symbol_info_tick(symbol)
    except Exception:
        return None
    if info is None:
        return None
    bid = float(getattr(info, "bid", 0) or 0)
    ask = float(getattr(info, "ask", 0) or 0)
    if bid and ask:
        return (bid + ask) / 2
    return bid or ask or None


def intermarket_snapshot(overrides: dict[str, float] | None = None) -> IntermarketSnapshot:
    prices: dict[str, float] = dict(overrides or {})
    source = "override" if overrides else "none"
    if not prices:
        yf_ok = module_available("yfinance")
        mt5_ok = module_available("MetaTrader5")
        for key, candidates in SYMBOLS.items():
            value = None
            if yf_ok:
                for cand in candidates:
                    value = _yfinance_last(cand)
                    if value is not None:
                        source = "yfinance"
                        break
            if value is None and mt5_ok:
                for cand in candidates:
                    value = _mt5_last(cand)
                    if value is not None:
                        source = "mt5"
                        break
            if value is not None:
                prices[key] = value
        if not prices:
            if yf_ok:
                source = "yfinance_empty"
            elif mt5_ok:
                source = "mt5_empty"
            else:
                source = "unavailable"

    notes: list[str] = []
    dxy = prices.get("dxy")
    xau = prices.get("xau")
    xag = prices.get("xag")
    if dxy is not None and xau is not None:
        notes.append("Inverse DXY/gold is the default confluence; decoupling is a panic tell.")
    if xag is not None and xau is not None:
        notes.append("Silver leading a break often pulls gold with a lag.")
    return IntermarketSnapshot(prices=prices, notes=notes, source=source)


def divergence_matrix(prev: dict[str, float], curr: dict[str, float]) -> dict[str, Any]:
    """If DXY makes a new high while gold fails a new low, flag bullish gold divergence."""
    out: dict[str, Any] = {}
    if "dxy" in prev and "dxy" in curr and "xau" in prev and "xau" in curr:
        dxy_high = curr["dxy"] > prev["dxy"]
        gold_not_lower = curr["xau"] >= prev["xau"]
        out["gold_bullish_vs_dxy"] = bool(dxy_high and gold_not_lower)
    return out
