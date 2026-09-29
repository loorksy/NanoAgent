"""
title: Mokli
author: Mokli
author_url: https://github.com/loorksy/NanoAgent
funding_url: https://github.com/loorksy/NanoAgent
version: 0.1.0
license: MIT
description: Streams a Mokli Agent API session (SSE) into Mokli as the "mokli" model. Translates gateway events into status / embeds / files / confirmation / notification events.
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

log = logging.getLogger("mokli.pipe")

API_PREFIX = "/api/v2"
SESSION_HEADER = "X-Mokli-Session"
MODEL_ID = "mokli"
MODEL_NAME = "Mokli"
CANCEL_TIMEOUT_SECONDS = 5.0
MAX_RECONNECTS = 1

RUN_SCOPED_KINDS = frozenset(
    {"delta", "state", "tool", "subagent", "structured", "artifact", "approval", "end"}
)

DEFAULT_LABELS: dict[str, str] = {
    "state.working": "Working",
    "state.processing": "Processing",
    "activity.step.started": "Working on a step",
    "activity.step.completed": "Step finished",
    "activity.step.failed": "Step failed",
    "activity.subagent": "Specialist",
    "diagnostics.title": "Developer diagnostics",
    "retry.waiting": "Retrying the model",
    "retry.recovered": "Retry succeeded",
    "retry.exhausted": "Retry failed",
    "retry.cleared": "Using another provider",
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
    "error.cancel": "Stop did not reach the agent. The run may still be active.",
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
        log.debug("mokli pipe: dropping non-JSON SSE payload")
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
            json={"id": session, "client": "mokli-ui"},
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
        model: str | None = None,
    ) -> str:
        payload: dict[str, object] = {
            "role": "user",
            "content": text,
            "locale": locale,
            "client": "mokli-ui",
        }
        if attachments:
            payload["attachments"] = attachments
        # Always send the selector value. null clears a previous override so the
        # settings primary runs; a catalog id selects that model for this chat.
        payload["model"] = model
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


def format_duration_ms(duration_ms: int) -> str:
    """Show the measured duration. Sub-second values stay in milliseconds."""
    if duration_ms < 1000:
        return f"{duration_ms} ms"
    seconds = duration_ms / 1000
    if abs(seconds - round(seconds)) < 0.05:
        return f"{int(round(seconds))} s"
    return f"{seconds:.1f} s"


def _fallback_step_label(stage: str, label: Callable[[str], str] | None = None) -> str:
    if stage == "failed":
        key = "activity.step.failed"
    elif stage in {"finished", "completed"}:
        key = "activity.step.completed"
    else:
        key = "activity.step.started"
    if label is not None:
        return label(key)
    return DEFAULT_LABELS[key]


def _tool_label(
    data: Mapping[str, object],
    stage: str,
    label: Callable[[str], str] | None = None,
) -> str:
    display = _as_str(data.get("display"))
    if display:
        return display
    return _fallback_step_label(stage, label)


def _role_label(role: str, label: Callable[[str], str] | None = None) -> str:
    if role and not ("_" in role or (role.isascii() and role.islower())):
        return role
    if label is not None:
        return label("activity.subagent")
    return DEFAULT_LABELS["activity.subagent"]


def project_activity(events: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """Visible activity steps derived only from real tool and subagent events."""
    steps: list[dict[str, object]] = []
    index: dict[str, dict[str, object]] = {}
    for event in events:
        kind = _as_str(event.get("kind"))
        data = _as_dict(event.get("data"))
        stage = _as_str(data.get("event"), "started")
        if kind == "tool":
            call_id = _as_str(data.get("call_id")) or f"tool-{len(steps)}"
            if stage == "started" or call_id not in index:
                step = {
                    "id": call_id,
                    "kind": "tool",
                    "label": _tool_label(data, "started"),
                    "technical": _as_str(data.get("name")),
                    "done": False,
                }
                steps.append(step)
                index[call_id] = step
            if stage in {"finished", "failed"}:
                current = index.get(call_id)
                if current is not None:
                    current["label"] = _tool_label(data, stage)
                    current["done"] = True
                    current["failed"] = stage == "failed"
        elif kind == "subagent" and stage == "started":
            sub_id = _as_str(data.get("id")) or f"sub-{len(steps)}"
            if sub_id in index:
                continue
            step = {
                "id": sub_id,
                "kind": "subagent",
                "label": _role_label(_as_str(data.get("role"))),
                "technical": _as_str(data.get("role")),
                "done": False,
            }
            steps.append(step)
            index[sub_id] = step
        elif kind == "subagent" and stage in {"finished", "failed"}:
            current = index.get(_as_str(data.get("id")))
            if current is not None:
                current["done"] = True
                current["failed"] = stage == "failed"
        elif kind == "retry":
            state = _as_str(data.get("state"))
            label_key = {
                "waiting": "retry.waiting",
                "recovered": "retry.recovered",
                "exhausted": "retry.exhausted",
                "cleared": "retry.cleared",
            }.get(state)
            if label_key is None:
                continue
            attempt_n = _as_int(data.get("attempt"))
            attempt = str(attempt_n if attempt_n is not None else 0)
            step_id = "fallback" if state == "cleared" else f"retry-{attempt}"
            label = DEFAULT_LABELS[label_key]
            done = state in {"recovered", "exhausted", "cleared"}
            failed = state == "exhausted"
            current = index.get(step_id)
            if current is None:
                current = {
                    "id": step_id,
                    "kind": "retry",
                    "label": label,
                    "technical": state,
                    "done": done,
                    "failed": failed,
                }
                steps.append(current)
                index[step_id] = current
            else:
                current["label"] = label
                current["technical"] = state
                current["done"] = done
                current["failed"] = failed
    return steps


def activity_line(steps: list[Mapping[str, object]]) -> str:
    parts: list[str] = []
    for step in steps:
        label = _as_str(step.get("label")) or DEFAULT_LABELS["activity.step.started"]
        if step.get("failed"):
            parts.append(label)
        elif step.get("done"):
            parts.append(f"{label} ✓")
        else:
            parts.append(f"{label} …")
    return " · ".join(parts)


def closing_description(
    steps: list[Mapping[str, object]],
    outcome_label: str,
    *,
    ok: bool,
) -> str:
    """Keep the real activity line when a turn ends successfully.

    A generic outcome would replace that line in the chat status history.
    A failed or cancelled turn still names the outcome, after the steps.
    """
    line = activity_line(steps) if steps else ""
    if not line:
        return outcome_label
    if ok:
        return line
    return f"{line} · {outcome_label}"


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
        self.submitted = False
        self.last_event_id: str | None = None
        self.finished = False
        self.timeline: list[str] = []
        self.embeds: list[str] = []
        self.files: list[dict[str, object]] = []
        self.steps: list[dict[str, object]] = []
        self.diagnostics: dict[str, object] | None = None

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
            description="Base URL of the Mokli Agent API (no trailing slash).",
        )
        GATEWAY_TOKEN: str = Field(
            default="",
            description="Bearer token for the Agent API (scopes: chat, approve). Stop uses chat.",
        )
        DEFAULT_LOCALE: str = Field(
            default="en",
            description="Locale used for labels/results when Mokli does not send one.",
        )
        SHOW_TIMELINE: bool = Field(
            default=True,
            description="Append a collapsible tool/subagent timeline to each reply.",
        )
        SHOW_DIAGNOSTICS: bool = Field(
            default=False,
            description="Developer only: append measured token and timing diagnostics.",
        )
        REQUEST_TIMEOUT: float = Field(
            default=30.0, description="Connect/REST timeout in seconds (SSE reads never time out)."
        )

    def __init__(self) -> None:
        self.valves = self.Valves()
        self.transport: httpx.AsyncBaseTransport | None = None
        self._labels_cache: dict[str, dict[str, str]] = {}

    def pipes(self) -> list[dict[str, str]]:
        models = [{"id": MODEL_ID, "name": MODEL_NAME}]
        seen = {MODEL_ID}
        for row in self._catalog_models():
            model_id = row["id"]
            if model_id in seen:
                continue
            seen.add(model_id)
            models.append({"id": model_id, "name": row["name"] or model_id})
        return models

    def _catalog_models(self) -> list[dict[str, str]]:
        token = self.valves.GATEWAY_TOKEN.strip()
        base = self.valves.GATEWAY_URL.rstrip("/")
        if not token or not base:
            return []
        try:
            response = httpx.get(
                f"{base}/api/v2/chat/models",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            response.raise_for_status()
            payload: object = response.json()
        except Exception:
            log.warning("mokli pipe: model list unavailable")
            return []
        body = _as_dict(payload)
        rows = body.get("models")
        found: list[dict[str, str]] = []
        for raw in _as_list(rows):
            row = _as_dict(raw)
            model_id = _as_str(row.get("id")).strip()
            if not model_id:
                continue
            name = _as_str(row.get("name")).strip() or model_id
            found.append({"id": model_id, "name": name})
        return found

    def _requested_model(self, body: Mapping[str, object]) -> str | None:
        """Provider model id from the chat selector, or None for the settings primary.

        Mokli names a manifold pipe ``<function id>.<pipe id>``. The
        installed function id is ``mokli``. A provider/model id may itself
        contain dots (``openai/gpt-4.1``), so only a function-id prefix is
        stripped.
        """
        raw = _as_str(body.get("model")).strip()
        if not raw or raw == MODEL_ID:
            return None
        if raw.startswith(f"{MODEL_ID}."):
            chosen = raw[len(MODEL_ID) + 1 :].strip()
            if not chosen or chosen == MODEL_ID:
                return None
            return chosen
        if "." in raw:
            head, tail = raw.split(".", 1)
            tail = tail.strip()
            if head and "/" not in head and "/" in tail:
                if not tail or tail == MODEL_ID:
                    return None
                return tail
        return raw

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
        for candidate in (metadata.get("session_id"), body.get("session_id")):
            session_id = _as_str(candidate).strip()
            if session_id and session_id != "local":
                return f"owui-{session_id}"
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
            log.warning("mokli pipe: labels unavailable for %s: %s", locale, exc)
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
                        if not turn.submitted:
                            turn.run_id = await gateway.send_message(
                                session,
                                text,
                                attachments,
                                locale,
                                self._requested_model(body),
                            )
                            turn.submitted = True
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
                    if not turn.submitted:
                        raise
                    log.warning("mokli pipe: stream dropped (%s)", exc)
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
                    if (turn.submitted or turn.run_id) and not turn.finished:
                        await self._cancel_quietly(gateway, session)
                    break
                attempt += 1
            if self.valves.SHOW_TIMELINE and turn.timeline:
                yield self._render_timeline(turn)
            if self.valves.SHOW_DIAGNOSTICS and turn.diagnostics:
                yield self._render_diagnostics(turn)
        except httpx.HTTPError as exc:
            log.error("mokli pipe: gateway error: %s", exc)
            detail = self._gateway_failure_text(exc, turn)
            await self._emit(
                __event_emitter__,
                {
                    "type": "status",
                    "data": {"description": detail, "done": True},
                },
            )
            yield f"\n\n{detail}"
        except (GeneratorExit, asyncio.CancelledError):
            if (turn.submitted or turn.run_id) and not turn.finished:
                if not await self._cancel_quietly(gateway, session):
                    await self._emit(
                        __event_emitter__,
                        {
                            "type": "status",
                            "data": {"description": turn.label("error.cancel"), "done": True},
                        },
                    )
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
        elif kind == "retry":
            await self._on_retry(data, turn, emitter)
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
        elif kind == "diagnostic":
            if self.valves.SHOW_DIAGNOSTICS:
                turn.diagnostics = data
        elif kind == "end":
            outcome = _as_str(data.get("outcome"), "ok")
            await self._emit(
                emitter,
                {
                    "type": "status",
                    "data": {
                        "description": closing_description(
                            turn.steps,
                            turn.label(f"outcome.{outcome}"),
                            ok=outcome == "ok",
                        ),
                        "done": True,
                    },
                },
            )
            turn.finished = True
        return []

    async def _on_state(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        state = _as_str(data.get("state"), "working")
        if state == "working" and turn.steps:
            await self._emit(
                emitter,
                {
                    "type": "status",
                    "data": {"description": activity_line(turn.steps), "done": False},
                },
            )
            return
        description = turn.label(f"state.{state}")
        phase = _as_str(data.get("phase"))
        provider_thinking = data.get("provider_thinking") is True
        if state == "working" and phase in {"thinking", "processing", "tool"} and not provider_thinking:
            description = turn.label("state.processing")
        elif phase and not phase.startswith("tool:"):
            phase_kind, _, phase_name = phase.partition(":")
            description = f"{description} · {turn.label(f'phase.{phase_kind}', phase_kind)}"
            if phase_name and phase_kind != "tool":
                description = f"{description} {phase_name}"
        waiting_for = _as_dict(data.get("waiting_for"))
        if waiting_for:
            waiting_kind = _as_str(waiting_for.get("kind"))
            if waiting_kind:
                description = f"{description} · {turn.label(f'waiting.{waiting_kind}')}"
        outcome = _as_str(data.get("outcome"))
        if state == "completed" and (outcome or turn.steps):
            description = closing_description(
                turn.steps,
                turn.label(f"outcome.{outcome or 'ok'}"),
                ok=(outcome or "ok") == "ok",
            )
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
        call_id = _as_str(data.get("call_id")) or f"tool-{len(turn.steps)}"
        label = _tool_label(data, stage, turn.label)
        existing = next((step for step in turn.steps if step.get("id") == call_id), None)
        if existing is None:
            turn.steps.append(
                {
                    "id": call_id,
                    "kind": "tool",
                    "label": label,
                    "technical": name,
                    "done": stage in {"finished", "failed"},
                    "failed": stage == "failed",
                }
            )
        else:
            existing["label"] = label
            existing["done"] = stage in {"finished", "failed"}
            existing["failed"] = stage == "failed"
        await self._emit(
            emitter,
            {
                "type": "status",
                "data": {"description": activity_line(turn.steps), "done": False},
            },
        )
        detail = f"{label} · {name}" if name else label
        if duration is not None:
            detail = f"{detail} · {format_duration_ms(duration)}"
        arguments = _as_str(data.get("arguments"))
        if arguments:
            detail = f"{detail} · {arguments}"
        if summary:
            detail = f"{detail} · {summary}"
        turn.timeline.append(detail)

    async def _on_retry(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        state = _as_str(data.get("state"))
        label_key = {
            "waiting": "retry.waiting",
            "recovered": "retry.recovered",
            "exhausted": "retry.exhausted",
            "cleared": "retry.cleared",
        }.get(state)
        if label_key is None:
            return
        attempt_n = _as_int(data.get("attempt"))
        attempt = str(attempt_n if attempt_n is not None else 0)
        step_id = "fallback" if state == "cleared" else f"retry-{attempt}"
        label = turn.label(label_key)
        done = state in {"recovered", "exhausted", "cleared"}
        failed = state == "exhausted"
        existing = next((step for step in turn.steps if step.get("id") == step_id), None)
        if existing is None:
            turn.steps.append(
                {
                    "id": step_id,
                    "kind": "retry",
                    "label": label,
                    "technical": state,
                    "done": done,
                    "failed": failed,
                }
            )
        else:
            existing["label"] = label
            existing["technical"] = state
            existing["done"] = done
            existing["failed"] = failed
        await self._emit(
            emitter,
            {
                "type": "status",
                "data": {"description": activity_line(turn.steps), "done": False},
            },
        )
        detail = f"{label} · {attempt}"
        error_kind = _as_str(data.get("error_kind"))
        if error_kind:
            detail = f"{detail} · {error_kind}"
        turn.timeline.append(detail)

    async def _on_subagent(
        self, data: Mapping[str, object], turn: _Turn, emitter: EventEmitter | None
    ) -> None:
        stage = _as_str(data.get("event"), "started")
        role = _as_str(data.get("role")) or _as_str(data.get("id"))
        summary = _as_str(data.get("summary"))
        duration = _as_int(data.get("duration_ms"))
        sub_id = _as_str(data.get("id")) or f"sub-{len(turn.steps)}"
        label = _role_label(role, turn.label)
        existing = next((step for step in turn.steps if step.get("id") == sub_id), None)
        if stage == "started" and existing is None:
            turn.steps.append(
                {
                    "id": sub_id,
                    "kind": "subagent",
                    "label": label,
                    "technical": role,
                    "done": False,
                    "failed": False,
                }
            )
        elif existing is not None and stage in {"finished", "failed"}:
            existing["done"] = True
            existing["failed"] = stage == "failed"
        if turn.steps:
            await self._emit(
                emitter,
                {
                    "type": "status",
                    "data": {"description": activity_line(turn.steps), "done": False},
                },
            )
        detail = f"{label} · {role}" if role else label
        if duration is not None:
            detail = f"{detail} · {format_duration_ms(duration)}"
        if summary:
            detail = f"{detail} · {summary}"
        turn.timeline.append(detail)

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
                log.warning("mokli pipe: result html %s failed: %s", result_id, exc)
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
            log.warning("mokli pipe: confirmation dialog failed: %s", exc)
            turn.timeline.append(f"{turn.label('approval.pending')}: {summary}".rstrip(": "))
            return
        confirmed = bool(result)
        try:
            await gateway.resolve_approval(turn.session, approval_id, confirmed)
        except httpx.HTTPError as exc:
            log.warning("mokli pipe: approval %s not delivered: %s", approval_id, exc)
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
    def _gateway_failure_text(exc: httpx.HTTPError, turn: _Turn) -> str:
        """Prefer the gateway's own error over the generic unreachable message."""
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                body = response.json()
            except Exception:
                body = None
            if isinstance(body, dict):
                err = body.get("error")
                if isinstance(err, dict):
                    details = err.get("details") if isinstance(err.get("details"), dict) else {}
                    if str(err.get("code") or "") == "unknown_model":
                        model = str(details.get("model") or "").strip()
                        if model:
                            return f"Unknown model: {model}"
                    message = err.get("message")
                    if isinstance(message, str) and message.strip():
                        return message.strip()
        return turn.label("error.gateway")

    @staticmethod
    async def _emit(emitter: EventEmitter | None, event: dict[str, object]) -> bool:
        if emitter is None:
            return False
        try:
            await emitter(event)
        except Exception as exc:
            log.warning("mokli pipe: event %s rejected: %s", event.get("type"), exc)
            return False
        return True

    @staticmethod
    async def _cancel_quietly(gateway: GatewayClient, session: str) -> bool:
        try:
            await asyncio.wait_for(gateway.cancel(session), timeout=CANCEL_TIMEOUT_SECONDS)
        except BaseException as exc:
            log.warning("mokli pipe: cancel for %s failed: %s", session, exc)
            return False
        return True

    @staticmethod
    def _render_timeline(turn: _Turn) -> str:
        lines = "\n".join(f"- {entry}" for entry in turn.timeline)
        return (
            f"\n\n<details>\n<summary>{turn.label('timeline.title')}</summary>\n\n"
            f"{lines}\n\n</details>\n"
        )

    @staticmethod
    def _render_diagnostics(turn: _Turn) -> str:
        payload = turn.diagnostics or {}
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        return (
            "\n\n<details>\n<summary>"
            f"{turn.label('diagnostics.title')}</summary>\n\n"
            f"```json\n{body}\n```\n\n</details>\n"
        )
