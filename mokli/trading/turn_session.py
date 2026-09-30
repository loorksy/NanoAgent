"""Turn-scoped mutable state for the gold agent loop.

RequestContext stays a frozen routing snapshot. Tools read ``current_turn_session()``.
The ContextVar is bound per operator turn by ``AgentLoop._process_message``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from mokli.trading.evidence.context import PipelineContext
from mokli.trading.gold import DATA_SYMBOL

_CURRENT_TURN_SESSION: ContextVar["TurnSession | None"] = ContextVar(
    "mokli_trading_turn_session",
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
    decision_wire: str | None = None
    # A failed analysis in this turn. The next call returns it and does not
    # start the team or the kernel again. A stored success wins over this.
    decision_error: str | None = None
    live_plan_block: str | None = None
    # session key, recommendation id, graded row, quote. A later price display
    # does not read this; it fetches its own tick.
    live_grade: tuple[str, str, dict[str, Any], Any] | None = None
    quote_display: dict[str, str | None] = field(default_factory=dict)
    candle_reuses: int = 0
    calendar_reuses: int = 0
    quote_reuses: int = 0
    _candle_cache: dict[tuple[str, str, int], tuple[Any, ...]] = field(default_factory=dict)
    _calendar_cache: dict[int, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    _fetch_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _candle_inflight: dict[tuple[str, str, int], threading.Event] = field(
        default_factory=dict, repr=False
    )
    _calendar_inflight: dict[int, threading.Event] = field(default_factory=dict, repr=False)
    _shared_inflight: dict[Any, dict[str, Any]] = field(default_factory=dict, repr=False)

    def take_cached_candles(self, symbol: str, interval: str, limit: int) -> tuple[Any, ...] | None:
        """Candles already fetched in this turn for the same symbol, interval, and limit."""
        hit = self._candle_cache.get((symbol, interval, limit))
        if hit is None:
            return None
        self.candle_reuses += 1
        return hit

    def remember_candles(self, symbol: str, interval: str, limit: int, candles: list[Any]) -> None:
        self._candle_cache[(symbol, interval, limit)] = tuple(candles)

    def take_cached_calendar(self, limit: int) -> tuple[dict[str, Any], ...] | None:
        """Calendar rows already downloaded in this turn for the same limit."""
        hit = self._calendar_cache.get(limit)
        if hit is None:
            return None
        self.calendar_reuses += 1
        return hit

    def remember_calendar(self, limit: int, events: list[dict[str, Any]]) -> None:
        self._calendar_cache[limit] = tuple(dict(row) for row in events)

    def load_candles(
        self,
        symbol: str,
        interval: str,
        limit: int,
        fetch: Callable[[], list[Any]],
    ) -> list[Any]:
        """One in-flight download per symbol, interval, and limit."""

        def _fetch() -> tuple[Any, ...]:
            return tuple(fetch())

        loaded = self._join(
            (symbol, interval, limit),
            self._candle_cache,
            self._candle_inflight,
            _fetch,
            lambda: setattr(self, "candle_reuses", self.candle_reuses + 1),
        )
        return [] if loaded is None else list(loaded)

    def load_calendar(
        self,
        limit: int,
        fetch: Callable[[], list[dict[str, Any]] | None],
    ) -> list[dict[str, Any]] | None:
        """One in-flight calendar download per limit. A failure is not stored."""

        def _fetch() -> tuple[dict[str, Any], ...] | None:
            rows = fetch()
            if rows is None:
                return None
            return tuple(dict(row) for row in rows)

        loaded = self._join(
            limit,
            self._calendar_cache,
            self._calendar_inflight,
            _fetch,
            lambda: setattr(self, "calendar_reuses", self.calendar_reuses + 1),
        )
        if loaded is None:
            return None
        return [dict(row) for row in loaded]

    def _join(
        self,
        key: Any,
        cache: dict[Any, Any],
        inflight: dict[Any, threading.Event],
        fetch: Callable[[], Any],
        on_reuse: Callable[[], None],
    ) -> Any:
        while True:
            with self._fetch_lock:
                hit = cache.get(key)
                if hit is not None:
                    on_reuse()
                    return hit
                event = inflight.get(key)
                leader = event is None
                if leader:
                    event = threading.Event()
                    inflight[key] = event
            if not leader:
                event.wait()
                continue
            try:
                value = fetch()
                if value is None:
                    return None
                with self._fetch_lock:
                    cache[key] = value
                return value
            finally:
                with self._fetch_lock:
                    if inflight.get(key) is event:
                        inflight.pop(key, None)
                event.set()

    def share_inflight(
        self,
        key: Any,
        fetch: Callable[[], Any],
        *,
        on_reuse: Callable[[], None] | None = None,
    ) -> Any:
        """Join a download that is already running. A finished download is not reused."""
        while True:
            with self._fetch_lock:
                state = self._shared_inflight.get(key)
                if state is None:
                    state = {
                        "event": threading.Event(),
                        "waiters": 0,
                        "value": None,
                        "error": None,
                        "ready": False,
                    }
                    self._shared_inflight[key] = state
                    leader = True
                    event = state["event"]
                else:
                    state["waiters"] += 1
                    leader = False
                    event = state["event"]
            if leader:
                try:
                    value = fetch()
                except Exception as exc:
                    state["error"] = exc
                    raise
                else:
                    state["value"] = value
                    return value
                finally:
                    with self._fetch_lock:
                        state["ready"] = True
                        if state["waiters"] == 0 and self._shared_inflight.get(key) is state:
                            self._shared_inflight.pop(key, None)
                    event.set()
            event.wait()
            error = state["error"]
            value = state["value"]
            with self._fetch_lock:
                state["waiters"] -= 1
                if (
                    state["waiters"] == 0
                    and state["ready"]
                    and self._shared_inflight.get(key) is state
                ):
                    self._shared_inflight.pop(key, None)
            if error is not None:
                raise error
            if on_reuse is not None:
                on_reuse()
            return value

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
