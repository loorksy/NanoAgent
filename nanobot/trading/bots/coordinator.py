"""Foxagent-style bot scanner coordinator."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from nanobot.trading.market_context import build_agent_market_context
from nanobot.trading.oanda import fetch_quote


@dataclass
class BotSignal:
    agent: str
    symbol: str
    direction: str
    reason: str
    price: float | None
    ts: int


@dataclass
class BotCycleResult:
    signals: list[BotSignal] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


def run_bot_cycle(enabled_agents: list[str] | None = None) -> BotCycleResult:
    agents = enabled_agents or ["news_candle", "multi_strategy", "pattern_notes"]
    result = BotCycleResult()
    market = build_agent_market_context()
    quote = fetch_quote("XAUUSD")
    price = quote.mid if quote else market.last_close
    now = int(time.time() * 1000)

    if "multi_strategy" in agents:
        if market.atr > 0 and len(market.candles) >= 20:
            last = market.candles[-1]
            body = abs(last.close - last.open)
            if body > market.atr * 0.8:
                direction = "buy" if last.close > last.open else "sell"
                sig = BotSignal(
                    agent="multi_strategy",
                    symbol="XAUUSD",
                    direction=direction,
                    reason="Impulse candle vs ATR",
                    price=price,
                    ts=now,
                )
                result.signals.append(sig)
                result.alerts.append(f"Bot signal: {direction} impulse on XAUUSD @ {price}")

    if "pattern_notes" in agents and market.candles:
        rng = max(c.high for c in market.candles[-10:]) - min(c.low for c in market.candles[-10:])
        if rng < market.atr * 2:
            result.alerts.append("Bot note: compressed range on XAUUSD — watch for expansion")

    return result
