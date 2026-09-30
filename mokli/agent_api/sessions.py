"""Client sessions ↔ ``AgentLoop`` session keys; run submission, cancel, timeline.

A run is one ``process_direct`` turn executed in a task owned by this module so
that a client disconnect never cancels the agent and ``cancel`` can stop it.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypedDict, cast

from loguru import logger

from mokli.agent.hook import AgentHook, AgentHookContext
from mokli.agent.tools.display import phrase_for
from mokli.agent.turn_diagnostics import latest_diagnostics
from mokli.agent_api.approvals import ApprovalRegistry
from mokli.agent_api.db import Database, row_to_dict
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import (
    AGENT_API_CHANNEL,
    GatewayEvent,
    JsonObject,
    Outcome,
    delta_data,
    now_ms,
    session_id_for_key,
    session_key_for,
    subagent_data,
    tool_data,
    translate_runtime_event,
)
from mokli.agent_api.hub import EventHub
from mokli.agent_api.ids import new_id
from mokli.bus.runtime_events import TurnCompleted
from mokli.events import AgentEvent
from mokli.providers.base import ToolCallRequest

TIMELINE_KINDS: tuple[str, ...] = (
    "state",
    "tool",
    "subagent",
    "structured",
    "artifact",
    "approval",
    "notification",
    "job",
    "end",
)
_SUMMARY_LIMIT = 240
_SENSITIVE_TOOLS = frozenset({
    "mt5_get_account",
    "mt5_propose_order",
    "mt5_confirm_order",
    "mt5_modify_order",
    "mt5_close_position",
    "mt5_cancel_order",
})
_SUBAGENT_TOOLS = frozenset({"spawn", "trading_team"})


class AgentLoopLike(Protocol):
    """The slice of :class:`mokli.agent.loop.AgentLoop` the Agent API relies on."""

    def process_direct(self, *args: Any, **kwargs: Any) -> Awaitable[object]: ...


class SessionRecord(TypedDict):
    id: str
    title: str
    created_at: int
    updated_at: int
    archived: bool
    state: str


def _summary(value: object) -> str:
    text = str(value if not hasattr(value, "content") else getattr(value, "content", ""))
    text = " ".join(text.split())
    if len(text) > _SUMMARY_LIMIT:
        return text[: _SUMMARY_LIMIT - 1] + "…"
    return text


def _response_text(value: object) -> str:
    if value is None:
        return ""
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    return str(value)


class TurnHook(AgentHook):
    """Project tool / subagent lifecycle into public ``tool`` and ``subagent`` events."""

    def __init__(
        self,
        hub: EventHub,
        approvals: ApprovalRegistry,
        *,
        session: str,
        run: str,
    ) -> None:
        super().__init__()
        self._hub = hub
        self._approvals = approvals
        self._session = session
        self._run = run
        self._started: dict[str, float] = {}

    def _emit_tool(
        self,
        event: str,
        tool_call: ToolCallRequest,
        *,
        summary: str | None = None,
        arguments: str | None = None,
    ) -> None:
        started = self._started.pop(tool_call.id, None)
        duration = int((time.monotonic() - started) * 1000) if started is not None else None
        display = phrase_for(tool_call.name, event)
        if event == "started":
            data = tool_data(
                "started",
                name=tool_call.name,
                call_id=tool_call.id,
                display=display,
                arguments=arguments,
            )
        elif event == "failed":
            data = tool_data(
                "failed",
                name=tool_call.name,
                call_id=tool_call.id,
                summary=summary,
                duration_ms=duration,
                display=display,
            )
        else:
            data = tool_data(
                "finished",
                name=tool_call.name,
                call_id=tool_call.id,
                summary=summary,
                duration_ms=duration,
                display=display,
            )
        self._hub.publish(self._session, "tool", data, run=self._run)

    @staticmethod
    def _public_arguments(name: str, params: object) -> str | None:
        if name in _SENSITIVE_TOOLS or not isinstance(params, dict):
            return None
        text = json.dumps(params, ensure_ascii=False, default=str)
        if len(text) > 180:
            return text[:179] + "…"
        return text

    async def before_execute_tool(
        self,
        context: AgentHookContext,
        tool_call: ToolCallRequest,
        tool: object,
        params: object,
    ) -> None:
        self._started[tool_call.id] = time.monotonic()
        self._emit_tool(
            "started",
            tool_call,
            arguments=self._public_arguments(tool_call.name, params),
        )
        if tool_call.name in _SUBAGENT_TOOLS:
            role = ""
            if isinstance(params, dict):
                role_value = cast(dict[str, object], params).get("role") or cast(
                    dict[str, object], params,
                ).get("task")
                role = str(role_value or "")[:80]
            self._hub.publish(
                self._session,
                "subagent",
                subagent_data("started", id=tool_call.id, role=role or tool_call.name),
                run=self._run,
            )

    async def after_execute_tool(
        self,
        context: AgentHookContext,
        tool_call: ToolCallRequest,
        tool: object,
        params: object,
        result: object,
    ) -> None:
        summary = None if tool_call.name in _SENSITIVE_TOOLS else _summary(result)
        self._emit_tool("finished", tool_call, summary=summary)
        if tool_call.name in _SUBAGENT_TOOLS:
            self._hub.publish(
                self._session,
                "subagent",
                subagent_data(
                    "finished", id=tool_call.id, role=tool_call.name, summary=_summary(result),
                ),
                run=self._run,
            )
        if tool_call.name == "mt5_propose_order":
            self._register_proposal(result)

    async def emit_reasoning(self, reasoning_content: str | None) -> None:
        # A non-empty provider delta is the only thinking signal. Later chunks
        # of the same stretch do not publish again.
        if not reasoning_content:
            return
        self._hub.working(
            self._session,
            "thinking",
            run=self._run,
            provider_thinking=True,
        )

    async def emit_reasoning_end(self) -> None:
        current = self._hub.state.snapshot(self._session)
        if current["phase"] != "thinking" or not current["provider_thinking"]:
            return
        self._hub.working(self._session, "processing", run=self._run)

    async def on_execute_tool_error(
        self,
        context: AgentHookContext,
        tool_call: ToolCallRequest,
        tool: object,
        params: object,
        error: object,
    ) -> None:
        self._emit_tool("failed", tool_call, summary=_summary(error))

    def _register_proposal(self, result: object) -> None:
        raw = str(result)
        try:
            parsed: object = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(parsed, dict):
            return
        payload = cast(dict[str, object], parsed)
        proposal = payload.get("proposal")
        if not isinstance(proposal, dict):
            return
        proposal_map = cast(dict[str, object], proposal)
        proposal_id = proposal_map.get("id")
        if not isinstance(proposal_id, str):
            return
        self._approvals.open_from_proposal(
            proposal_map, session=self._session, run=self._run,
        )


class SessionService:
    """Own the public session registry and the per-session run task."""

    def __init__(
        self,
        agent: AgentLoopLike,
        hub: EventHub,
        approvals: ApprovalRegistry,
        db: Database,
        *,
        request_timeout: float = 900.0,
    ) -> None:
        self._agent = agent
        self.hub = hub
        self.approvals = approvals
        self._db = db
        self._runs: dict[str, asyncio.Task[None]] = {}
        self._run_ids: dict[str, str] = {}
        self._request_timeout = request_timeout

    # -- registry ----------------------------------------------------------

    def create(self, *, title: str = "", session_id: str | None = None) -> SessionRecord:
        sid = session_id or new_id("s_")
        now = now_ms()
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO api_sessions(id, title, created_at, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET archived_at = NULL, updated_at = excluded.updated_at",
                (sid, title, now, now),
            )
        record = self.get(sid)
        assert record is not None
        return record

    def ensure(self, session_id: str) -> SessionRecord:
        found = self.get(session_id)
        if found is not None:
            return found
        return self.create(session_id=session_id)

    def get(self, session_id: str) -> SessionRecord | None:
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT id, title, created_at, updated_at, archived_at FROM api_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._record(row_to_dict(row))

    def list(self, *, include_archived: bool = False) -> list[SessionRecord]:
        where = "" if include_archived else "WHERE archived_at IS NULL "
        with self._db.cursor() as cur:
            rows = cur.execute(
                "SELECT id, title, created_at, updated_at, archived_at FROM api_sessions "
                f"{where}ORDER BY updated_at DESC",
            ).fetchall()
        return [self._record(row_to_dict(row)) for row in rows]

    async def delete(self, session_id: str) -> bool:
        if self.get(session_id) is None:
            return False
        await self.cancel(session_id)
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE api_sessions SET archived_at = ? WHERE id = ?",
                (now_ms(), session_id),
            )
        discard = getattr(self._agent, "discard_session", None)
        if callable(discard):
            try:
                await cast(Callable[[str], Awaitable[None]], discard)(session_key_for(session_id))
            except Exception:
                logger.warning("agent_api discard_session failed", exc_info=True)
        return True

    def _record(self, row: dict[str, object]) -> SessionRecord:
        sid = str(row["id"])
        created = row.get("created_at")
        updated = row.get("updated_at")
        return {
            "id": sid,
            "title": str(row.get("title") or ""),
            "created_at": created if isinstance(created, int) else 0,
            "updated_at": updated if isinstance(updated, int) else 0,
            "archived": row.get("archived_at") is not None,
            "state": self.hub.state.snapshot(sid)["state"],
        }

    def _touch(self, session_id: str) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE api_sessions SET updated_at = ? WHERE id = ?", (now_ms(), session_id),
            )

    def use_model(self, session_id: str, model_id: str) -> bool:
        """Select the provider model for the next turn of this chat.

        Returns false when ``model_id`` is not a model the user selected.
        """
        from mokli.api.chat_models import apply_session_model

        return apply_session_model(self._agent, session_key_for(session_id), model_id)

    def busy_run(self, session_id: str) -> str | None:
        """Run id when this session already has a task that has not finished."""
        task = self._runs.get(session_id)
        if task is not None and not task.done():
            return self._run_ids.get(session_id)
        return None

    def clear_model(self, session_id: str) -> bool:
        """Use the settings primary for the next turn of this chat."""
        from mokli.api.chat_models import clear_session_model

        return clear_session_model(self._agent, session_key_for(session_id))

    # -- runs --------------------------------------------------------------

    def active_run(self, session_id: str) -> str | None:
        return self._run_ids.get(session_id)

    def submit(
        self,
        session_id: str,
        text: str,
        *,
        media: list[str] | None = None,
        locale: str | None = None,
    ) -> str:
        if not text.strip() and not media:
            raise ApiError(400, "empty_message")
        self.ensure(session_id)
        in_flight = self.busy_run(session_id)
        if in_flight:
            raise ApiError(409, "run_in_progress", details={"run": in_flight})
        run_id = new_id("r_")
        self._run_ids[session_id] = run_id
        self.hub.run_started(session_id, run_id)
        task = asyncio.create_task(
            self._run(session_id, run_id, text, media or [], locale),
            name=f"agent-api-run:{session_id}",
        )
        self._runs[session_id] = task
        self._touch(session_id)
        return run_id

    async def _run(
        self,
        session_id: str,
        run_id: str,
        text: str,
        media: list[str],
        locale: str | None = None,
    ) -> None:
        key = session_key_for(session_id)
        hook = TurnHook(self.hub, self.approvals, session=session_id, run=run_id)
        emitted = False

        async def on_stream(token: str) -> None:
            nonlocal emitted
            if token:
                emitted = True
                self.hub.publish(session_id, "delta", delta_data(token), run=run_id)

        async def on_stream_end(*_args: object, **_kwargs: object) -> None:
            return None

        outcome: Outcome = "ok"
        try:
            async with asyncio.timeout(self._request_timeout):
                response = await self._agent.process_direct(
                    content=text,
                    media=media or None,
                    session_key=key,
                    channel=AGENT_API_CHANNEL,
                    chat_id=session_id,
                    on_stream=on_stream,
                    on_stream_end=on_stream_end,
                    hooks=[hook],
                    attributes={"locale": locale} if locale else None,
                )
            if not emitted:
                final = _response_text(response)
                if final.strip():
                    self.hub.publish(session_id, "delta", delta_data(final), run=run_id)
        except asyncio.CancelledError:
            outcome = "cancelled"
        except asyncio.TimeoutError:
            outcome = "error"
            logger.warning("agent_api run {} timed out", run_id)
        except Exception:
            outcome = "error"
            logger.exception("agent_api run {} failed", run_id)
        finally:
            if self._run_ids.get(session_id) == run_id:
                self._run_ids.pop(session_id, None)
                self._runs.pop(session_id, None)
            measured = latest_diagnostics(key)
            if measured is not None:
                self.hub.publish(session_id, "diagnostic", measured, run=run_id)
            self.hub.run_finished(session_id, run_id, outcome)

    async def cancel(self, session_id: str) -> bool:
        task = self._runs.get(session_id)
        cancelled = False
        if task is not None and not task.done():
            task.cancel()
            cancelled = True
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        canceller = getattr(self._agent, "cancel_session", None) or getattr(
            self._agent, "_cancel_active_tasks", None,
        )
        if callable(canceller):
            try:
                count = await cast(Callable[[str], Awaitable[int]], canceller)(
                    session_key_for(session_id),
                )
                cancelled = cancelled or bool(count)
            except Exception:
                logger.exception("agent_api cancel failed for {}", session_id)
        return cancelled

    # -- timeline ----------------------------------------------------------

    def timeline(self, session_id: str, *, after: str | None = None) -> list[GatewayEvent]:
        return [
            event
            for event in self.hub.log.after(session_id, after)
            if event["kind"] in TIMELINE_KINDS
        ]


class RuntimeEventBridge:
    """Subscribe to the bus and mirror lifecycle events for every session into the hub."""

    def __init__(self, hub: EventHub) -> None:
        self._hub = hub
        self._unsubscribe: Callable[[], None] | None = None

    def attach(self, subscribe: Callable[[Callable[[AgentEvent], None]], Callable[[], None]]) -> None:
        self._unsubscribe = subscribe(self.handle)

    def detach(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def handle(self, event: AgentEvent) -> None:
        translated = translate_runtime_event(event)
        if translated is None:
            return
        session = translated["session"]
        if translated["kind"] == "state":
            state_value = translated["data"].get("state")
            if state_value == "completed":
                # Agent API runs own their completion (ordering with deltas / end).
                if self._hub.state.active_run(session) is not None:
                    return
                outcome = translated["data"].get("outcome")
                self._hub.run_finished(
                    session,
                    None,
                    cast(Outcome, outcome if isinstance(outcome, str) else "ok"),
                )
                return
            phase = translated["data"].get("phase")
            self._hub.working(session, str(phase or "processing"))
            return
        data: JsonObject = translated["data"]
        self._hub.publish(session, translated["kind"], data)


def is_turn_completed(event: AgentEvent) -> bool:
    return isinstance(event, TurnCompleted)


__all__ = [
    "AgentLoopLike",
    "RuntimeEventBridge",
    "SessionRecord",
    "SessionService",
    "TurnHook",
    "session_id_for_key",
]
