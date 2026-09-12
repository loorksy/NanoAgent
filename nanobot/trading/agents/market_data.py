"""Market data agent — wraps build_agent_market_context."""

from __future__ import annotations

from nanobot.trading.market_context import build_agent_market_context
from nanobot.trading.types import AgentMarketContext


def run_market_data_agent(symbol: str = "XAUUSD", interval: str = "15m") -> AgentMarketContext:
    return build_agent_market_context(symbol=symbol, interval=interval)
