"""Compact frozen evidence text for trading team subagents."""

from __future__ import annotations

import json

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
    return json.dumps(payload, ensure_ascii=False)


_CANDLE_ROLE_FILES = frozenset({
    "structure",
    "timeframe",
    "mtf_synthesizer",
    "liquidity",
    "scenario",
})


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
    return json.dumps(scoped, ensure_ascii=False)
