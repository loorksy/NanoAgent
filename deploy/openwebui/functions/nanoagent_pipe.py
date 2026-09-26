"""
title: NanoAgent
author: NanoAgent
author_url: https://github.com/loorksy/NanoAgent
funding_url: https://github.com/loorksy/NanoAgent
version: 0.1.0
license: MIT
description: Streams a NanoAgent Agent API session (SSE) into Open WebUI as the "nanoagent" model. Translates gateway events into status / embeds / files / confirmation / notification events.
requirements: httpx>=0.27,pydantic>=2
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Iterable, Mapping
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypedDict, cast

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger("nanoagent.pipe")

API_PREFIX = "/api/v2"
SESSION_HEADER = "X-NanoAgent-Session"
MODEL_ID = "nanoagent"
MODEL_NAME = "NanoAgent"
CANCEL_TIMEOUT_SECONDS = 5.0
MAX_RECONNECTS = 1

RUN_SCOPED_KINDS = frozenset(
    {"delta", "state", "tool", "subagent", "structured", "artifact", "approval", "end"}
)

DEFAULT_LABELS: dict[str, str] = {
    "state.working": "Working",
    "state.waiting": "Waiting",
    "state.completed": "Completed",
    "phase.queued": "Queued",
    "phase.thinking": "Thinking",
    "phase.streaming": "Responding",
    "phase.tool": "Using tool",
    "phase.subagent": "Delegating",
    "waiting.approval": "Awaiting approval",
    "waiting.input": "Awaiting input",
    "outcome.ok": "Done",
    "outcome.cancelled": "Cancelled",
    "outcome.error": "Failed",
    "outcome.expired": "Expired",
    "tool.started": "Running tool",
    "tool.finished": "Tool finished",
    "tool.failed": "Tool failed",
    "subagent.started": "Subagent started",
    "subagent.finished": "Subagent finished",
    "approval.execution": "Confirm order execution",
    "approval.modify": "Confirm order modification",
    "approval.close": "Confirm position close",
    "approval.generic": "Confirm action",
    "approval.confirmed": "Approved",
    "approval.cancelled": "Rejected",
    "approval.pending": "Awaiting approval",
    "approval.failed": "Decision could not be delivered",
    "job.update": "Task update",
    "result.title": "Result",
    "result.field": "Field",
    "result.value": "Value",
    "timeline.title": "Agent timeline",
    "error.gateway": "The agent gateway is unreachable.",
    "error.stream": "The event stream ended before the agent finished.",
}

EventEmitter = Callable[[dict[str, object]], Awaitable[None]]
EventCall = Callable[[dict[str, object]], Awaitable[object]]


class GatewayEvent(TypedDict, total=False):
    id: str
    session: str
    run: str
    ts: int
    kind: str
    data: dict[str, object]


class Attachment(TypedDict):
    type: str
    url: str


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        raw = cast(dict[object, object], value)
        return {str(key): item for key, item in raw.items()}
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return list(cast(list[object], value))
    return []


def _as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


# --------------------------------------------------------------------------- SSE


class SSEMessage:
    __slots__ = ("data", "event", "id")

    def __init__(self, data: str, id: str | None = None, event: str | None = None) -> None:
        self.data = data
        self.id = id
        self.event = event

    def __repr__(self) -> str:
        return f"SSEMessage(data={self.data!r}, id={self.id!r}, event={self.event!r})"


class SSEParser:
    """Incremental text/event-stream parser (WHATWG EventSource semantics)."""

    def __init__(self) -> None:
        self._buffer = ""
        self._data: list[str] = []
        self._event: str | None = None
        self._has_fields = False
        self.last_event_id: str | None = None
        self.retry_ms: int | None = None

    def feed(self, chunk: str) -> list[SSEMessage]:
        self._buffer += chunk
        messages: list[SSEMessage] = []
        while True:
            newline = self._buffer.find("\n")
            carriage = self._buffer.find("\r")
            ends = [index for index in (newline, carriage) if index != -1]
            if not ends:
                break
            end = min(ends)
            cut = end + 1
            if self._buffer[end] == "\r":
                if end + 1 == len(self._buffer):
                    break
                if self._buffer[end + 1] == "\n":
                    cut = end + 2
            line = self._buffer[:end]
            self._buffer = self._buffer[cut:]
            message = self.feed_line(line)
            if message is not None:
                messages.append(message)
        return messages

    def feed_lines(self, lines: Iterable[str]) -> list[SSEMessage]:
        messages: list[SSEMessage] = []
        for line in lines:
            message = self.feed_line(line.rstrip("\r\n"))
            if message is not None:
                messages.append(message)
        return messages

    def feed_line(self, line: str) -> SSEMessage | None:
        if line == "":
            return self._dispatch()
        if line.startswith(":"):
            return None
        name, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if name == "data":
            self._data.append(value)
            self._has_fields = True
        elif name == "id":
            if "\0" not in value:
                self.last_event_id = value
        elif name == "event":
            self._event = value
            self._has_fields = True
        elif name == "retry":
            try:
                self.retry_ms = int(value)
            except ValueError:
                pass
        return None

    def flush(self) -> SSEMessage | None:
        if self._buffer:
            pending = self._buffer
            self._buffer = ""
            self.feed_line(pending.rstrip("\r\n"))
        return self._dispatch()

    def _dispatch(self) -> SSEMessage | None:
        if not self._has_fields:
            return None
        data = "\n".join(self._data)
        event = self._event
        self._data = []
        self._event = None
        self._has_fields = False
        if not data:
            return None
        return SSEMessage(data=data, id=self.last_event_id, event=event)


def parse_gateway_event(message: SSEMessage) -> GatewayEvent | None:
    try:
        raw: object = json.loads(message.data)
    except ValueError:
        log.debug("nanoagent pipe: dropping non-JSON SSE payload")
        return None
    body = _as_dict(raw)
    if not body:
        return None
    kind = _as_str(body.get("kind")) or _as_str(message.event)
    if not kind:
        return None
    event: GatewayEvent = {"kind": kind, "data": _as_dict(body.get("data"))}
    event_id = _as_str(body.get("id")) or (message.id or "")
    if event_id:
        event["id"] = event_id
    session = _as_str(body.get("session"))
    if session:
        event["session"] = session
    run = _as_str(body.get("run"))
    if run:
        event["run"] = run
    ts = _as_int(body.get("ts"))
    if ts is not None:
        event["ts"] = ts
    return event


# ----------------------------------------------------------------- Gateway client


class SessionNotFoundError(Exception):
    pass


class EventStream:
    """Open SSE connection to ``GET /sessions/{id}/events``; iterate with :meth:`events`."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        session: str,
        after: str | None,
        create_session: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._client = client
        self._session = session
        self._after = after
        self._create_session = create_session
        self._context: AbstractAsyncContextManager[httpx.Response] | None = None
        self._response: httpx.Response | None = None

    async def _open(self) -> None:
        params: dict[str, str] = {}
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
        if self._after:
            params["after"] = self._after
            headers["Last-Event-ID"] = self._after
        context = self._client.stream(
            "GET",
            f"{API_PREFIX}/sessions/{self._session}/events",
            params=params,
            headers=headers,
            timeout=httpx.Timeout(self._client.timeout.connect, read=None),
        )
        response = await context.__aenter__()
        if response.status_code == 404:
            await context.__aexit__(None, None, None)
            raise SessionNotFoundError(self._session)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            await context.__aexit__(None, None, None)
            raise
        self._context = context
        self._response = response

    async def __aenter__(self) -> EventStream:
        try:
            await self._open()
        except SessionNotFoundError:
            if self._create_session is None:
                raise
            await self._create_session(self._session)
            await self._open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        context = self._context
        self._context = None
        self._response = None
        if context is not None:
            await context.__aexit__(exc_type, exc, tb)

    async def events(self) -> AsyncGenerator[GatewayEvent, None]:
        response = self._response
        if response is None:
            raise RuntimeError("EventStream used outside of its context")
        parser = SSEParser()
        async for chunk in response.aiter_text():
            for message in parser.feed(chunk):
                event = parse_gateway_event(message)
                if event is not None:
                    yield event
        tail = parser.flush()
        if tail is not None:
            event = parse_gateway_event(tail)
            if event is not None:
                yield event


class GatewayClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _session_headers(session: str) -> dict[str, str]:
        return {SESSION_HEADER: session}

    async def create_session(self, session: str) -> None:
        response = await self._client.post(
            f"{API_PREFIX}/sessions",
            json={"id": session, "client": "open-webui"},
            headers=self._session_headers(session),
        )
        response.raise_for_status()

    def open_events(self, session: str, after: str | None) -> EventStream:
        return EventStream(self._client, session, after, self.create_session)

    async def send_message(
        self,
        session: str,
        text: str,
        attachments: list[Attachment],
        locale: str,
    ) -> str:
        payload: dict[str, object] = {
            "role": "user",
            "content": text,
            "locale": locale,
            "client": "open-webui",
        }
        if attachments:
            payload["attachments"] = attachments
        url = f"{API_PREFIX}/sessions/{session}/messages"
        response = await self._client.post(
            url, json=payload, headers=self._session_headers(session)
        )
        if response.status_code == 404:
            await self.create_session(session)
            response = await self._client.post(
                url, json=payload, headers=self._session_headers(session)
            )
        response.raise_for_status()
        body: object = response.json()
        return _as_str(_as_dict(body).get("run_id"))

    async def cancel(self, session: str) -> None:
        response = await self._client.post(
            f"{API_PREFIX}/sessions/{session}/cancel",
            headers=self._session_headers(session),
            timeout=httpx.Timeout(CANCEL_TIMEOUT_SECONDS),
        )
        response.raise_for_status()

    async def resolve_approval(self, session: str, approval_id: str, confirm: bool) -> None:
        response = await self._client.post(
            f"{API_PREFIX}/approvals/{approval_id}",
            json={"decision": "confirm" if confirm else "cancel"},
            headers=self._session_headers(session),
        )
        response.raise_for_status()

    async def result_html(self, result_id: str, locale: str) -> str:
        response = await self._client.get(
            f"{API_PREFIX}/results/{result_id}/html",
            params={"locale": locale},
            headers={"Accept": "text/html"},
        )
        response.raise_for_status()
        return response.text

    async def labels(self, locale: str) -> dict[str, str]:
        response = await self._client.get(f"{API_PREFIX}/labels", params={"locale": locale})
        response.raise_for_status()
        body: object = response.json()
        table = _as_dict(body)
        nested = _as_dict(table.get("labels"))
        if nested:
            table = nested
        return {key: value for key, value in table.items() if isinstance(value, str)}


# -------------------------------------------------------------------- helpers


def extract_last_user_message(body: Mapping[str, object]) -> tuple[str, list[Attachment]]:
    messages = _as_list(body.get("messages"))
    for raw in reversed(messages):
        message = _as_dict(raw)
        if _as_str(message.get("role")) != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content, []
        texts: list[str] = []
        attachments: list[Attachment] = []
        for part_raw in _as_list(content):
            part = _as_dict(part_raw)
            part_type = _as_str(part.get("type"))
            if part_type == "text":
                texts.append(_as_str(part.get("text")))
            elif part_type == "image_url":
                url = _as_str(_as_dict(part.get("image_url")).get("url"))
                if url:
                    attachments.append({"type": "image", "url": url})
            elif part_type == "input_audio":
                url = _as_str(_as_dict(part.get("input_audio")).get("data"))
                if url:
                    attachments.append({"type": "audio", "url": url})
        return "\n".join(text for text in texts if text), attachments
    return "", []


def _escape_cell(value: object) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str)
    return text.replace("|", "\\|").replace("\n", " ")


def payload_to_markdown_table(
    payload: Mapping[str, object], labels: Mapping[str, str], title: str
) -> str:
    field_label = labels.get("result.field", "Field")
    value_label = labels.get("result.value", "Value")
    lines = [
        f"**{title}**",
        "",
        f"| {field_label} | {value_label} |",
        "| --- | --- |",
    ]
    for key, value in payload.items():
        lines.append(f"| {_escape_cell(key)} | {_escape_cell(value)} |")
    return "\n".join(lines)


def _task_response(task: str, body: Mapping[str, object]) -> str:
    text, _ = extract_last_user_message(body)
    if task == "title_generation":
        title = " ".join(text.split())[:60] or MODEL_NAME
        return json.dumps({"title": title}, ensure_ascii=False)
    if task == "tags_generation":
        return json.dumps({"tags": []})
    if task == "follow_up_generation":
        return json.dumps({"follow_ups": []})
    if task in ("query_generation", "emoji_generation", "autocomplete_generation"):
        return json.dumps({})
    return ""


class _Turn:
    def __init__(self, session: str, locale: str, labels: dict[str, str]) -> None:
        self.session = session
        self.locale = locale
        self.labels = labels
        self.run_id = ""
        self.last_event_id: str | None = None
        self.finished = False
        self.timeline: list[str] = []
        self.embeds: list[str] = []
        self.files: list[dict[str, object]] = []

    def label(self, key: str, fallback: str | None = None) -> str:
        found = self.labels.get(key) or DEFAULT_LABELS.get(key)
        if found:
            return found
        if fallback is not None:
            return fallback
        return key.rsplit(".", 1)[-1].replace("_", " ").capitalize()


# ------------------------------------------------------------------------ Pipe


class Pipe:
    class Valves(BaseModel):
        GATEWAY_URL: str = Field(
            default="http://127.0.0.1:8766",
            description="Base URL of the NanoAgent Agent API (no trailing slash).",
        )
        GATEWAY_TOKEN: str = Field(
            default="", description="Bearer token for the Agent API (scopes: chat, approve)."
        )
        DEFAULT_LOCALE: str = Field(
            default="en",
            description="Locale used for labels/results when Open WebUI does not send one.",
        )
        SHOW_TIMELINE: bool = Field(
            default=True,
            description="Append a collapsible tool/subagent timeline to each reply.",
        )
        REQUEST_TIMEOUT: float = Field(
            default=30.0, description="Connect/REST timeout in seconds (SSE reads never time out)."
        )

    def __init__(self) -> None:
        self.valves = self.Valves()
        self.transport: httpx.AsyncBaseTransport | None = None
        self._labels_cache: dict[str, dict[str, str]] = {}

    def pipes(self) -> list[dict[str, str]]:
        return [{"id": MODEL_ID, "name": MODEL_NAME}]

    # -- wiring -------------------------------------------------------------

    def _gateway(self) -> GatewayClient:
        return GatewayClient(
            base_url=self.valves.GATEWAY_URL,
            token=self.valves.GATEWAY_TOKEN,
            timeout=self.valves.REQUEST_TIMEOUT,
            transport=self.transport,
        )

    def _session_id(self, metadata: Mapping[str, object], body: Mapping[str, object]) -> str:
        for candidate in (metadata.get("chat_id"), body.get("chat_id")):
            chat_id = _as_str(candidate)
            if chat_id and chat_id != "local":
                return chat_id
        return f"owui-{uuid.uuid4().hex}"

    def _locale(self, metadata: Mapping[str, object]) -> str:
        variables = _as_dict(metadata.get("variables"))
        locale = _as_str(variables.get("{{USER_LANGUAGE}}")).strip()
        return locale or self.valves.DEFAULT_LOCALE

    async def _labels_for(self, gateway: GatewayClient, locale: str) -> dict[str, str]:
        cached = self._labels_cache.get(locale)
        if cached is not None:
            return cached
        try:
            fetched = await gateway.labels(locale)
        except httpx.HTTPError as exc:
            log.warning("nanoagent pipe: labels unavailable for %s: %s", locale, exc)
            return dict(DEFAULT_LABELS)
        merged = dict(DEFAULT_LABELS)
        merged.update(fetched)
        self._labels_cache[locale] = merged
        return merged

    # -- entry point --------------------------------------------------------

    async def pipe(
        self,
        body: dict[str, object],
        __user__: dict[str, object] | None = None,
        __metadata__: dict[str, object] | None = None,
        __event_emitter__: EventEmitter | None = None,
        __event_call__: EventCall | None = None,
        __task__: str | None = None,
    ) -> AsyncIterator[str]:
        metadata: Mapping[str, object] = __metadata__ or {}
        task = __task__ or _as_str(metadata.get("task"))
        if task:
            yield _task_response(task, body)
            return

        text, attachments = extract_last_user_message(body)
        if not text and not attachments:
            return

        session = self._session_id(metadata, body)
        locale = self._locale(metadata)
        gateway = self._gateway()
        turn = _Turn(session=session, locale=locale, labels={})
        try:
            turn.labels = await self._labels_for(gateway, locale)
            attempt = 0
            while True:
                try:
                    # The stream is opened before the message is posted so that no
                    # event emitted between POST and GET is lost.
                    async with gateway.open_events(session, turn.last_event_id) as stream:
                        if not turn.run_id:
                            turn.run_id = await gateway.send_message(
                                session, text, attachments, locale
                            )
                        events = stream.events()
                        try:
                            async for event in events:
                                for chunk in await self._handle_event(
                                    event, turn, gateway, __event_emitter__, __event_call__
                                ):
                                    yield chunk
                                if turn.finished:
                                    break
                        finally:
                            await events.aclose()
                except httpx.HTTPStatusError:
                    raise
                except httpx.HTTPError as exc:
                    if not turn.run_id:
                        raise
                    log.warning("nanoagent pipe: stream dropped (%s)", exc)
                if turn.finished:
                    break
                if attempt >= MAX_RECONNECTS:
                    await self._emit(
                        __event_emitter__,
                        {
                            "type": "status",
                            "data": {"description": turn.label("error.stream"), "done": True},
                        },
                    )
                    break
                attempt += 1
            if self.valves.SHOW_TIMELINE and turn.timeline:
                yield self._render_timeline(turn)
        except httpx.HTTPError as exc:
            log.error("nanoagent pipe: gateway error: %s", exc)
            await self._emit(
                __event_emitter__,
                {
                    "type": "status",
                    "data": {"description": turn.label("error.gateway"), "done": True},
                },
            )
            yield f"\n\n{turn.label('error.gateway')}"
        except (GeneratorExit, asyncio.CancelledError):
            if turn.run_id and not turn.finished:
                await self._cancel_quietly(gateway, session)
            raise
        finally:
            await gateway.aclose()

    # -- event dispatch -----------------------------------------------------

    async def _handle_event(
        self,
        event: GatewayEvent,
        turn: _Turn,
        gateway: GatewayClient,
        emitter: EventEmitter | None,
        caller: EventCall | None,
    ) -> list[str]:
        event_id = event.get("id")
        if event_id:
            turn.last_event_id = event_id
        kind = event.get("kind", "")
        run = event.get("run", "")
        if run and turn.run_id and run != turn.run_id and kind in RUN_SCOPED_KINDS:
            return []
        data = event.get("data", {})

        if kind == "delta":
            text = _as_str(data.get("text"))
            return [text] if text else []
        if kind == "state":
            await self._on_state(data, turn, emitter)
        elif kind == "tool":
            await self._on_tool(data, turn, emitter)
        elif kind == "subagent":
            await self._on_subagent(data, turn, emitter)
        elif kind == "structured":
            await self._on_structured(data, turn, gateway, emitter)
        elif kind == "artifact":
            await self._on_artifact(data, turn, emitter)
        elif kind == "approval":
            await self._on_approval(data, turn, gateway, emitter, caller)
        elif kind == "notification":
            await self._on_notification(data, emitter)
        elif kind == "job":
            self._on_job(data, turn)
        elif kind == "end":
            outcome = _as_str(data.get("outcome"), "ok")
            await self._emit(
                emitter,
                {
                    "type": "status",
                    "data": {"description": turn.label(f"outcome.{outcome}"), "done": True},
                },
            )
            turn.finished = True
        return []

    async def _on_state(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        state = _as_str(data.get("state"), "working")
        description = turn.label(f"state.{state}")
        phase = _as_str(data.get("phase"))
        if phase:
            phase_kind, _, phase_name = phase.partition(":")
            description = f"{description} · {turn.label(f'phase.{phase_kind}', phase_kind)}"
            if phase_name:
                description = f"{description} {phase_name}"
        waiting_for = _as_dict(data.get("waiting_for"))
        if waiting_for:
            waiting_kind = _as_str(waiting_for.get("kind"))
            if waiting_kind:
                description = f"{description} · {turn.label(f'waiting.{waiting_kind}')}"
        outcome = _as_str(data.get("outcome"))
        if state == "completed" and outcome:
            description = turn.label(f"outcome.{outcome}")
        await self._emit(
            emitter,
            {"type": "status", "data": {"description": description, "done": state == "completed"}},
        )

    async def _on_tool(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        stage = _as_str(data.get("event"), "started")
        name = _as_str(data.get("name"))
        summary = _as_str(data.get("summary"))
        duration = _as_int(data.get("duration_ms"))
        description = f"⚙ {turn.label(f'tool.{stage}')}: {name}".rstrip(": ")
        await self._emit(
            emitter, {"type": "status", "data": {"description": description, "done": False}}
        )
        entry = description
        if duration is not None:
            entry = f"{entry} ({duration} ms)"
        if summary:
            entry = f"{entry} - {summary}"
        turn.timeline.append(entry)

    async def _on_subagent(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        stage = _as_str(data.get("event"), "started")
        role = _as_str(data.get("role")) or _as_str(data.get("id"))
        summary = _as_str(data.get("summary"))
        description = f"↳ {turn.label(f'subagent.{stage}')}: {role}".rstrip(": ")
        await self._emit(
            emitter, {"type": "status", "data": {"description": description, "done": False}}
        )
        turn.timeline.append(f"{description} - {summary}" if summary else description)

    async def _on_structured(
        self,
        data: Mapping[str, object],
        turn: _Turn,
        gateway: GatewayClient,
        emitter: EventEmitter | None,
    ) -> None:
        result_type = _as_str(data.get("type"))
        result_id = _as_str(data.get("result_id"))
        payload = _as_dict(data.get("payload"))
        title = turn.label("result.title")
        if result_type:
            title = f"{title}: {result_type}"
        html = ""
        if result_id:
            try:
                html = await gateway.result_html(result_id, turn.locale)
            except httpx.HTTPError as exc:
                log.warning("nanoagent pipe: result html %s failed: %s", result_id, exc)
        if html:
            turn.embeds.append(html)
            sent = await self._emit(
                emitter,
                {"type": "embeds", "data": {"embeds": list(turn.embeds), "replace": True}},
            )
            if sent:
                return
        await self._emit(
            emitter,
            {
                "type": "message",
                "data": {"content": "\n\n" + payload_to_markdown_table(payload, turn.labels, title)},
            },
        )

    async def _on_artifact(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        url = _as_str(data.get("url"))
        if not url:
            return
        mime = _as_str(data.get("mime"))
        title = _as_str(data.get("title")) or _as_str(data.get("artifact_id"))
        if mime == "text/html":
            turn.embeds.append(url)
            await self._emit(
                emitter,
                {"type": "embeds", "data": {"embeds": list(turn.embeds), "replace": True}},
            )
            return
        file_entry: dict[str, object] = {
            "type": "image" if mime.startswith("image/") else "file",
            "url": url,
            "name": title,
        }
        if mime:
            file_entry["content_type"] = mime
        turn.files.append(file_entry)
        await self._emit(emitter, {"type": "files", "data": {"files": list(turn.files)}})

    async def _on_approval(
        self,
        data: Mapping[str, object],
        turn: _Turn,
        gateway: GatewayClient,
        emitter: EventEmitter | None,
        caller: EventCall | None,
    ) -> None:
        approval_id = _as_str(data.get("approval_id"))
        approval_type = _as_str(data.get("type"), "generic")
        summary = _as_str(data.get("summary"))
        title = turn.label(f"approval.{approval_type}", turn.label("approval.generic"))
        await self._emit(
            emitter,
            {
                "type": "status",
                "data": {"description": turn.label("approval.pending"), "done": False},
            },
        )
        if caller is None or not approval_id:
            turn.timeline.append(f"{turn.label('approval.pending')}: {summary}".rstrip(": "))
            return
        try:
            result = await caller(
                {"type": "confirmation", "data": {"title": title, "message": summary}}
            )
        except Exception as exc:
            log.warning("nanoagent pipe: confirmation dialog failed: %s", exc)
            turn.timeline.append(f"{turn.label('approval.pending')}: {summary}".rstrip(": "))
            return
        confirmed = bool(result)
        try:
            await gateway.resolve_approval(turn.session, approval_id, confirmed)
        except httpx.HTTPError as exc:
            log.warning("nanoagent pipe: approval %s not delivered: %s", approval_id, exc)
            failure = turn.label("approval.failed")
            await self._emit(
                emitter, {"type": "notification", "data": {"type": "error", "content": failure}}
            )
            turn.timeline.append(f"{failure}: {summary}".rstrip(": "))
            return
        verdict = turn.label("approval.confirmed" if confirmed else "approval.cancelled")
        await self._emit(
            emitter,
            {
                "type": "notification",
                "data": {"type": "success" if confirmed else "warning", "content": verdict},
            },
        )
        turn.timeline.append(f"{verdict}: {summary}".rstrip(": "))

    async def _on_notification(
        self, data: Mapping[str, object], emitter: EventEmitter | None
    ) -> None:
        level = _as_str(data.get("level"), "info").lower()
        level = {"warn": "warning", "critical": "error", "danger": "error"}.get(level, level)
        if level not in ("info", "success", "warning", "error"):
            level = "info"
        title = _as_str(data.get("title"))
        body_text = _as_str(data.get("body"))
        content = ": ".join(part for part in (title, body_text) if part)
        if not content:
            return
        await self._emit(
            emitter, {"type": "notification", "data": {"type": level, "content": content}}
        )

    def _on_job(self, data: Mapping[str, object], turn: _Turn) -> None:
        job_id = _as_str(data.get("job_id"))
        job_kind = _as_str(data.get("kind"))
        status = _as_str(data.get("status"))
        parts = [part for part in (job_kind, job_id, status) if part]
        if parts:
            turn.timeline.append(f"{turn.label('job.update')}: {' '.join(parts)}")

    # -- utilities ----------------------------------------------------------

    @staticmethod
    async def _emit(emitter: EventEmitter | None, event: dict[str, object]) -> bool:
        if emitter is None:
            return False
        try:
            await emitter(event)
        except Exception as exc:
            log.warning("nanoagent pipe: event %s rejected: %s", event.get("type"), exc)
            return False
        return True

    @staticmethod
    async def _cancel_quietly(gateway: GatewayClient, session: str) -> None:
        try:
            await asyncio.wait_for(gateway.cancel(session), timeout=CANCEL_TIMEOUT_SECONDS)
        except BaseException as exc:
            log.warning("nanoagent pipe: cancel for %s failed: %s", session, exc)

    @staticmethod
    def _render_timeline(turn: _Turn) -> str:
        lines = "\n".join(f"- {entry}" for entry in turn.timeline)
        return (
            f"\n\n<details>\n<summary>{turn.label('timeline.title')}</summary>\n\n"
            f"{lines}\n\n</details>\n"
        )
