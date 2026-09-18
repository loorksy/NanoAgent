"""Turn-scoped mutable state for the unified gold loop.

RequestContext stays a frozen routing snapshot. Tools read ``current_turn_session()``.
This ContextVar is only bound when LONORA_UNIFIED_LOOP is not off.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.gold import DATA_SYMBOL

_CURRENT_TURN_SESSION: ContextVar["TurnSession | None"] = ContextVar(
    "nanobot_trading_turn_session",
    default=None,
)

_NODE_ATTR = {
    "market_data": "market",
    "structure": "structure",
    "liquidity": "liquidity",
    "supply_demand": "supply_demand",
    "multi_timeframe": "mtf",
    "news": "news",
    "geometry": "geometry",
    "risk": "risk",
    "visual_capture": "visual",
}


@dataclass
class TurnSession:
    """Mutable evidence + kernel bookkeeping for one operator turn."""

    turn_id: str | None = None
    session_key: str | None = None
    interval: str = "15m"
    is_subagent: bool = False
    pipeline: PipelineContext | None = None
    tools_called: list[str] = field(default_factory=list)
    nodes_fetched: list[str] = field(default_factory=list)
    adjustments: list[str] = field(default_factory=list)
    authorized_prices: set[str] = field(default_factory=set)
    kernel_ran: bool = False
    kernel_decision: str | None = None
    kernel_result: Any | None = None
    quote_display: dict[str, str | None] = field(default_factory=dict)

    def ensure_pipeline(self, *, interval: str | None = None) -> PipelineContext:
        if interval:
            self.interval = interval
        if self.pipeline is None:
            self.pipeline = PipelineContext(symbol=DATA_SYMBOL, interval=self.interval)
        elif interval and self.pipeline.interval != interval and not self.nodes_fetched:
            self.pipeline.interval = interval
        return self.pipeline

    def present_nodes(self) -> frozenset[str]:
        ctx = self.pipeline
        if ctx is None:
            return frozenset()
        present: set[str] = set()
        for node_id, attr in _NODE_ATTR.items():
            if getattr(ctx, attr, None) is not None:
                present.add(node_id)
        return frozenset(present)

    def record_tool(self, name: str) -> None:
        self.tools_called.append(name)

    def add_price_strings(self, *values: object) -> None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                self.authorized_prices.add(text)


def bind_turn_session(session: TurnSession) -> Token[TurnSession | None]:
    return _CURRENT_TURN_SESSION.set(session)


def reset_turn_session(token: Token[TurnSession | None]) -> None:
    _CURRENT_TURN_SESSION.reset(token)


def current_turn_session() -> TurnSession | None:
    return _CURRENT_TURN_SESSION.get()


def require_turn_session() -> TurnSession:
    session = current_turn_session()
    if session is None:
        session = TurnSession()
        _CURRENT_TURN_SESSION.set(session)
    return session


@contextmanager
def turn_session_scope(session: TurnSession | None = None):
    bound = session or TurnSession()
    token = bind_turn_session(bound)
    try:
        yield bound
    finally:
        reset_turn_session(token)
