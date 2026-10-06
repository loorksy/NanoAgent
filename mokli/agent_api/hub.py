"""In-process fan-out of :class:`GatewayEvent` to SSE/WS subscribers, with write-through log."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Literal

from loguru import logger

from mokli.agent_api.event_log import EventLog
from mokli.agent_api.events import (
    EventKind,
    GatewayEvent,
    JsonObject,
    Outcome,
    StateData,
    end_data,
    now_ms,
)
from mokli.agent_api.ids import MonotonicIdGenerator
from mokli.agent_api.state import StateTracker

GlobalListener = Callable[[GatewayEvent], None]
_QUEUE_LIMIT = 2000


class Subscription:
    """One consumer's ordered queue for a single session."""

    def __init__(self, hub: EventHub, session: str) -> None:
        self._hub = hub
        self.session = session
        self.queue: asyncio.Queue[GatewayEvent] = asyncio.Queue(maxsize=_QUEUE_LIMIT)
        self.closed = False

    def push(self, event: GatewayEvent) -> None:
        if self.closed:
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("agent_api subscriber for {} is too slow; dropping event", self.session)

    async def get(self, timeout: float | None = None) -> GatewayEvent | None:
        if timeout is None:
            return await self.queue.get()
        try:
            return await asyncio.wait_for(self.queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self._hub._remove(self)  # pyright: ignore[reportPrivateUsage]


class EventHub:
    """Assign ids, persist, update derived state, and fan out events."""

    def __init__(self, log: EventLog, state: StateTracker | None = None) -> None:
        self.log = log
        self.state = state or StateTracker()
        self._ids = MonotonicIdGenerator()
        self._subs: dict[str, set[Subscription]] = {}
        self._global: list[GlobalListener] = []

    # -- subscriptions -----------------------------------------------------

    def subscribe(self, session: str) -> Subscription:
        sub = Subscription(self, session)
        self._subs.setdefault(session, set()).add(sub)
        return sub

    def _remove(self, sub: Subscription) -> None:
        subs = self._subs.get(sub.session)
        if subs is None:
            return
        subs.discard(sub)
        if not subs:
            self._subs.pop(sub.session, None)

    def has_listeners(self, session: str | None = None) -> bool:
        if session is None:
            return any(self._subs.values())
        return bool(self._subs.get(session))

    def add_global_listener(self, listener: GlobalListener) -> Callable[[], None]:
        self._global.append(listener)

        def _remove() -> None:
            if listener in self._global:
                self._global.remove(listener)

        return _remove

    # -- publication -------------------------------------------------------

    def publish(
        self,
        session: str,
        kind: EventKind,
        data: JsonObject,
        *,
        run: str | None = None,
    ) -> GatewayEvent:
        event: GatewayEvent = {
            "id": self._ids.next(),
            "session": session,
            "run": run,
            "ts": now_ms(),
            "kind": kind,
            "data": data,
        }
        try:
            self.log.append(event)
        except Exception:
            logger.exception("agent_api event log append failed")
        for sub in list(self._subs.get(session, ())):
            sub.push(event)
        for listener in list(self._global):
            try:
                listener(event)
            except Exception:
                logger.exception("agent_api global listener failed")
        return event

    def publish_state(
        self,
        session: str,
        state: StateData | None,
        *,
        run: str | None = None,
    ) -> GatewayEvent | None:
        if state is None:
            return None
        data: JsonObject = dict(state)
        waiting = state.get("waiting_for")
        if waiting is not None:
            data["waiting_for"] = dict(waiting)
        return self.publish(session, "state", data, run=run)

    # -- lifecycle helpers -------------------------------------------------

    def run_started(self, session: str, run: str) -> None:
        self.publish_state(session, self.state.run_started(session, run), run=run)

    def working(
        self,
        session: str,
        phase: str,
        *,
        run: str | None = None,
        provider_thinking: bool = False,
    ) -> None:
        self.publish_state(
            session,
            self.state.working(
                session, phase=phase, provider_thinking=provider_thinking,
            ),
            run=run or self.state.active_run(session),
        )

    def run_finished(self, session: str, run: str | None, outcome: Outcome) -> None:
        self.publish_state(session, self.state.run_finished(session, run, outcome), run=run)
        self.publish(session, "end", end_data(run, outcome), run=run)

    def approval_opened(self, session: str, approval_id: str) -> None:
        self.publish_state(
            session,
            self.state.approval_opened(session, approval_id),
            run=self.state.active_run(session),
        )

    def approval_resolved(
        self,
        session: str,
        approval_id: str,
        *,
        outcome: Literal["ok", "cancelled", "expired"],
    ) -> None:
        self.publish_state(
            session,
            self.state.approval_resolved(session, approval_id, outcome=outcome),
            run=self.state.active_run(session),
        )
