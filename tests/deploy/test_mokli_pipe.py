"""Tests for the Mokli Pipe Function in deploy/mokliui/functions/mokli_pipe.py.

The gateway is simulated with ``httpx.MockTransport`` so the pipe is exercised end to end
(message POST, SSE stream, approvals, result HTML, labels, cancel) without a running
Agent API.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from types import ModuleType

import httpx
import pytest

PIPE_PATH = (
    Path(__file__).resolve().parents[2] / "deploy" / "mokliui" / "functions" / "mokli_pipe.py"
)


def _load_pipe_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mokli_pipe_under_test", PIPE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pipe_mod = _load_pipe_module()

SESSION = "chat-123"
RUN = "run-1"


def sse(event: dict[str, object], event_id: str | None = None, name: str | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if name is not None:
        lines.append(f"event: {name}")
    lines.append("data: " + json.dumps(event))
    return "\n".join(lines) + "\n\n"


def ev(kind: str, data: dict[str, object], *, run: str | None = RUN) -> dict[str, object]:
    body: dict[str, object] = {"kind": kind, "data": data, "session": SESSION, "ts": 1}
    if run is not None:
        body["run"] = run
    return body


class ChunkStream(httpx.AsyncByteStream):
    def __init__(
        self,
        chunks: list[str],
        *,
        fail_after: bool = False,
        block_after: asyncio.Event | None = None,
    ) -> None:
        self._chunks = chunks
        self._fail_after = fail_after
        self._block_after = block_after

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk.encode("utf-8")
        if self._fail_after:
            raise httpx.ReadError("connection reset")
        if self._block_after is not None:
            await self._block_after.wait()


class FakeGateway:
    def __init__(
        self,
        streams: list[ChunkStream],
        *,
        session_exists: bool = True,
        labels: dict[str, str] | None = None,
        html: str | None = "<html><body>card</body></html>",
        html_status: int = 200,
        message_run_id: str | None = RUN,
        cancel_status: int = 200,
    ) -> None:
        self.streams = list(streams)
        self.sessions: set[str] = {SESSION} if session_exists else set()
        self.labels = labels or {}
        self.html = html
        self.html_status = html_status
        self.requests: list[httpx.Request] = []
        self.approvals: list[tuple[str, str]] = []
        self.labels_calls = 0
        self.message_run_id = message_run_id
        self.cancel_status = cancel_status

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def paths(self, method: str | None = None) -> list[str]:
        return [
            f"{request.method} {request.url.path}"
            + (f"?{request.url.query.decode()}" if request.url.query else "")
            for request in self.requests
            if method is None or request.method == method
        ]

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "GET" and path == "/api/v2/labels":
            self.labels_calls += 1
            return httpx.Response(200, json={"labels": self.labels})
        if request.method == "POST" and path == "/api/v2/sessions":
            payload = json.loads(request.content)
            self.sessions.add(payload["id"])
            return httpx.Response(201, json={"id": payload["id"]})
        match = re.fullmatch(r"/api/v2/sessions/([^/]+)/(events|messages|cancel)", path)
        if match:
            session, action = match.group(1), match.group(2)
            if session not in self.sessions:
                return httpx.Response(404, json={"error": {"code": "not_found"}})
            if action == "events":
                if not self.streams:
                    return httpx.Response(200, stream=ChunkStream([]))
                return httpx.Response(
                    200,
                    stream=self.streams.pop(0),
                    headers={"content-type": "text/event-stream"},
                )
            if action == "messages":
                body = {} if self.message_run_id is None else {"run_id": self.message_run_id}
                return httpx.Response(200, json=body)
            if action == "cancel":
                return httpx.Response(self.cancel_status, json={"ok": self.cancel_status < 400})
            return httpx.Response(200, json={"ok": True})
        match = re.fullmatch(r"/api/v2/approvals/([^/]+)", path)
        if match and request.method == "POST":
            decision = json.loads(request.content)["decision"]
            self.approvals.append((match.group(1), decision))
            return httpx.Response(200, json={"ok": True})
        match = re.fullmatch(r"/api/v2/results/([^/]+)/html", path)
        if match:
            if self.html is None or self.html_status != 200:
                return httpx.Response(self.html_status or 500, text="nope")
            return httpx.Response(200, text=self.html, headers={"content-type": "text/html"})
        return httpx.Response(500, text=f"unexpected {request.method} {path}")


class Harness:
    def __init__(
        self,
        gateway: FakeGateway,
        *,
        confirm: object = True,
        event_call: Callable[[dict[str, object]], Awaitable[object]] | None | bool = True,
        show_timeline: bool = True,
        emitter_fails_for: set[str] | None = None,
    ) -> None:
        self.gateway = gateway
        self.emitted: list[dict[str, object]] = []
        self.calls: list[dict[str, object]] = []
        self._confirm = confirm
        self._emitter_fails_for = emitter_fails_for or set()
        self.pipe = pipe_mod.Pipe()
        self.pipe.valves = self.pipe.Valves(
            GATEWAY_URL="http://gateway.test",
            GATEWAY_TOKEN="secret-token",
            DEFAULT_LOCALE="en",
            SHOW_TIMELINE=show_timeline,
            REQUEST_TIMEOUT=5,
        )
        self.pipe.transport = gateway.transport()
        self.event_call: Callable[[dict[str, object]], Awaitable[object]] | None
        if event_call is True:
            self.event_call = self._call
        elif event_call is False or event_call is None:
            self.event_call = None
        else:
            self.event_call = event_call

    async def _emit(self, event: dict[str, object]) -> None:
        if event["type"] in self._emitter_fails_for:
            raise RuntimeError("unsupported event")
        self.emitted.append(event)

    async def _call(self, event: dict[str, object]) -> object:
        self.calls.append(event)
        return self._confirm

    def body(self, text: str = "hello") -> dict[str, object]:
        return {
            "model": "mokli",
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "assistant", "content": "earlier"},
                {"role": "user", "content": text},
            ],
        }

    def metadata(self, **extra: object) -> dict[str, object]:
        data: dict[str, object] = {"chat_id": SESSION, "message_id": "m1", "session_id": "ws1"}
        data.update(extra)
        return data

    def generator(
        self, body: dict[str, object] | None = None, metadata: dict[str, object] | None = None
    ) -> AsyncIterator[str]:
        return self.pipe.pipe(
            body or self.body(),
            {"id": "u1", "name": "Operator", "role": "admin"},
            metadata if metadata is not None else self.metadata(),
            self._emit,
            self.event_call,
        )

    async def run(
        self, body: dict[str, object] | None = None, metadata: dict[str, object] | None = None
    ) -> list[str]:
        return [chunk async for chunk in self.generator(body, metadata)]

    def statuses(self) -> list[tuple[str, bool]]:
        return [
            (str(e["data"]["description"]), bool(e["data"]["done"]))  # type: ignore[index]
            for e in self.emitted
            if e["type"] == "status"
        ]

    def types(self) -> list[str]:
        return [str(e["type"]) for e in self.emitted]


# --------------------------------------------------------------------------- SSE parser


def test_sse_parser_handles_multiline_data_comments_and_split_chunks() -> None:
    parser = pipe_mod.SSEParser()
    raw = (
        ": keep-alive\n"
        "retry: 1500\n"
        "id: 7\n"
        "event: delta\n"
        "data: {\"kind\": \"delta\",\n"
        "data:  \"data\": {\"text\": \"a\"}}\n"
        "\r\n"
        "data:{\"kind\":\"end\",\"data\":{}}\r\n"
        "\r\n"
    )
    messages: list[object] = []
    for index in range(0, len(raw), 5):
        messages.extend(parser.feed(raw[index : index + 5]))
    assert len(messages) == 2
    first, second = messages
    assert first.id == "7" and first.event == "delta"
    assert json.loads(first.data) == {"kind": "delta", "data": {"text": "a"}}
    assert second.id == "7"  # last event id persists across messages
    assert second.event is None
    assert json.loads(second.data) == {"kind": "end", "data": {}}
    assert parser.retry_ms == 1500


def test_sse_parser_ignores_comment_only_blocks_and_null_ids() -> None:
    parser = pipe_mod.SSEParser()
    assert parser.feed(": ping\n\n") == []
    assert parser.feed("id: bad\0id\ndata: x\n\n")[0].id is None
    assert parser.feed("event: only\n\n") == []


def test_sse_parser_flush_dispatches_trailing_message() -> None:
    parser = pipe_mod.SSEParser()
    assert parser.feed('data: {"kind":"end","data":{}}') == []
    tail = parser.flush()
    assert tail is not None and json.loads(tail.data)["kind"] == "end"
    assert parser.flush() is None


def test_parse_gateway_event_uses_event_field_and_drops_garbage() -> None:
    message = pipe_mod.SSEMessage(data='{"data": {"text": "x"}, "id": "e1"}', event="delta")
    parsed = pipe_mod.parse_gateway_event(message)
    assert parsed == {"kind": "delta", "data": {"text": "x"}, "id": "e1"}
    assert pipe_mod.parse_gateway_event(pipe_mod.SSEMessage(data="not json")) is None
    assert pipe_mod.parse_gateway_event(pipe_mod.SSEMessage(data='{"data": {}}')) is None


def test_extract_last_user_message_supports_parts() -> None:
    body = {
        "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "look"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
                ],
            },
        ]
    }
    text, attachments = pipe_mod.extract_last_user_message(body)
    assert text == "look"
    assert attachments == [{"type": "image", "url": "data:image/png;base64,AA=="}]
    assert pipe_mod.extract_last_user_message({"messages": []}) == ("", [])


def test_closing_status_keeps_real_steps() -> None:
    steps = [
        {"label": "Checking the gold price", "done": True, "failed": False},
        {"label": "Could not read the gold price", "done": True, "failed": True},
    ]
    assert pipe_mod.closing_description(steps, "Done", ok=True) == (
        "Checking the gold price ✓ · Could not read the gold price"
    )
    assert pipe_mod.closing_description(steps, "Failed", ok=False) == (
        "Checking the gold price ✓ · Could not read the gold price · Failed"
    )
    assert pipe_mod.closing_description([], "Done", ok=True) == "Done"


def test_pipe_source_contains_no_arabic_or_fixed_rtl_text() -> None:
    source = PIPE_PATH.read_text(encoding="utf-8")
    assert re.search(r"[\u0600-\u06FF]", source) is None
    assert source.startswith('"""\ntitle: Mokli')
    assert "requirements:" in source.split('"""')[1]


# --------------------------------------------------------------------------- pipe flow


async def test_working_state_keeps_steps_that_already_ran() -> None:
    stream = ChunkStream(
        [
            sse(ev("tool", {"event": "started", "name": "web_search", "call_id": "c1",
                            "display": "Searching"}), "1"),
            sse(ev("state", {"state": "working", "phase": "thinking"}), "2"),
            sse(ev("end", {"run": RUN, "outcome": "ok"}), "3"),
        ]
    )
    harness = Harness(FakeGateway([stream]))
    await harness.run()
    descriptions = [text for text, _done in harness.statuses()]
    assert descriptions[0] == "Searching …"
    assert descriptions[1] == "Searching …"
    assert descriptions[-1] == "Searching …"
    assert harness.statuses()[-1][1] is True


async def test_in_progress_state_does_not_claim_a_reply_or_a_tool() -> None:
    stream = ChunkStream(
        [
            sse(ev("state", {"state": "working", "phase": "streaming"}), "1"),
            sse(ev("state", {"state": "working", "phase": "tool:get_gold_quote"}), "2"),
            sse(
                ev(
                    "state",
                    {"state": "working", "phase": "thinking", "provider_thinking": True},
                ),
                "3",
            ),
            sse(ev("end", {"run": RUN, "outcome": "ok"}), "4"),
        ]
    )
    harness = Harness(FakeGateway([stream]))
    await harness.run()
    descriptions = [text for text, _done in harness.statuses()]
    assert descriptions[0] == "Processing"
    assert descriptions[1] == "Processing"
    assert "get_gold_quote" not in descriptions[1]
    assert "Responding" not in descriptions[0]
    assert descriptions[2] == "Working · Thinking"


async def test_happy_path_streams_text_and_emits_events_in_order() -> None:
    stream = ChunkStream(
        [
            sse(ev("state", {"state": "working", "phase": "thinking"}), "1"),
            sse(ev("delta", {"text": "Hello"}), "2"),
            sse(ev("tool", {"event": "started", "name": "web_search", "call_id": "c1"}), "3"),
            sse(
                ev(
                    "tool",
                    {
                        "event": "finished",
                        "name": "web_search",
                        "call_id": "c1",
                        "summary": "3 hits",
                        "duration_ms": 120,
                    },
                ),
                "4",
            ),
            sse(ev("subagent", {"event": "started", "id": "sa1", "role": "analyst"}), "5"),
            sse(
                ev(
                    "structured",
                    {"type": "market", "result_id": "res-1", "payload": {"price": 2400}},
                ),
                "6",
            ),
            sse(ev("delta", {"text": " world"}), "7"),
            sse(ev("state", {"state": "completed", "outcome": "ok"}), "8"),
            sse(ev("end", {"run": RUN, "outcome": "ok"}), "9"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway)

    chunks = await harness.run()

    assert "".join(chunks[:2]) == "Hello world"
    timeline = chunks[-1]
    assert timeline.startswith("\n\n<details>")
    assert "<summary>Agent timeline</summary>" in timeline
    assert "web_search" in timeline
    assert "120 ms" in timeline
    assert "analyst" in timeline
    assert "⚙ Running tool: web_search" not in timeline
    web_rows = [line for line in timeline.splitlines() if "web_search" in line]
    assert web_rows == ["- web_search · finished · 120 ms · 3 hits"]

    assert harness.statuses() == [
        ("Processing", False),
        ("Working on a step …", False),
        ("Step finished ✓", False),
        ("Step finished ✓ · Specialist …", False),
        ("Step finished ✓ · Specialist …", True),
        ("Step finished ✓ · Specialist …", True),
    ]
    for description, _done in harness.statuses():
        assert "web_search" not in description
    embeds = [e for e in harness.emitted if e["type"] == "embeds"]
    assert embeds == [
        {"type": "embeds", "data": {"embeds": ["<html><body>card</body></html>"], "replace": True}}
    ]
    assert harness.types().index("embeds") < harness.types().index("status", 4)

    paths = gateway.paths()
    assert paths[0] == "GET /api/v2/labels?locale=en"
    assert paths[1] == f"GET /api/v2/sessions/{SESSION}/events"
    assert paths[2] == f"POST /api/v2/sessions/{SESSION}/messages"
    assert paths[3] == "GET /api/v2/results/res-1/html?locale=en"
    assert len(paths) == 4

    message_request = gateway.requests[2]
    assert message_request.headers["Authorization"] == "Bearer secret-token"
    assert message_request.headers["X-Mokli-Session"] == SESSION
    payload = json.loads(message_request.content)
    assert payload["content"] == "hello"
    assert payload["locale"] == "en"
    assert payload["model"] is None
    events_request = gateway.requests[1]
    assert events_request.headers["Accept"] == "text/event-stream"
    assert "after" not in events_request.url.params


async def test_session_is_created_when_gateway_returns_404() -> None:
    stream = ChunkStream(
        [sse(ev("delta", {"text": "hi"}), "1"), sse(ev("end", {"outcome": "ok"}), "2")]
    )
    gateway = FakeGateway([stream], session_exists=False)
    harness = Harness(gateway)

    chunks = await harness.run()

    assert chunks == ["hi"]
    assert gateway.paths() == [
        "GET /api/v2/labels?locale=en",
        f"GET /api/v2/sessions/{SESSION}/events",
        "POST /api/v2/sessions",
        f"GET /api/v2/sessions/{SESSION}/events",
        f"POST /api/v2/sessions/{SESSION}/messages",
    ]
    created = json.loads(gateway.requests[2].content)
    assert created["id"] == SESSION


@pytest.mark.parametrize(
    ("answer", "decision", "toast"),
    [(True, "confirm", "success"), (False, "cancel", "warning"), (None, "cancel", "warning")],
)
async def test_approval_round_trip(answer: object, decision: str, toast: str) -> None:
    stream = ChunkStream(
        [
            sse(ev("state", {"state": "waiting", "waiting_for": {"kind": "approval"}}), "1"),
            sse(
                ev(
                    "approval",
                    {
                        "approval_id": "ap-9",
                        "type": "execution",
                        "summary": "BUY 0.10 XAUUSD @ 2400",
                        "expires_at": 0,
                        "actions": ["confirm", "cancel"],
                    },
                ),
                "2",
            ),
            sse(ev("end", {"outcome": "ok"}), "3"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway, confirm=answer)

    chunks = await harness.run()

    assert harness.calls == [
        {
            "type": "confirmation",
            "data": {"title": "Confirm order execution", "message": "BUY 0.10 XAUUSD @ 2400"},
        }
    ]
    assert gateway.approvals == [("ap-9", decision)]
    approval_request = next(r for r in gateway.requests if "/approvals/" in r.url.path)
    assert approval_request.headers["X-Mokli-Session"] == SESSION
    notifications = [e for e in harness.emitted if e["type"] == "notification"]
    assert notifications == [{"type": "notification", "data": {"type": toast, "content": (
        "Approved" if decision == "confirm" else "Rejected"
    )}}]
    assert harness.statuses()[0] == ("Waiting · Awaiting approval", False)
    assert harness.statuses()[1] == ("Awaiting approval", False)
    assert any("BUY 0.10 XAUUSD" in chunk for chunk in chunks)


async def test_approval_delivery_failure_is_reported_not_fatal() -> None:
    stream = ChunkStream(
        [
            sse(ev("approval", {"approval_id": "ap-2", "type": "close", "summary": "s"}), "1"),
            sse(ev("delta", {"text": "after"}), "2"),
            sse(ev("end", {"outcome": "ok"}), "3"),
        ]
    )
    gateway = FakeGateway([stream])
    inner = gateway.handle

    async def flaky(request: httpx.Request) -> httpx.Response:
        if "/approvals/" in request.url.path:
            gateway.requests.append(request)
            return httpx.Response(500, json={"error": {"code": "boom"}})
        return await inner(request)

    harness = Harness(gateway, show_timeline=False)
    harness.pipe.transport = httpx.MockTransport(flaky)

    chunks = await harness.run()

    assert chunks == ["after"]
    notifications = [e for e in harness.emitted if e["type"] == "notification"]
    assert notifications == [
        {
            "type": "notification",
            "data": {"type": "error", "content": "Decision could not be delivered"},
        }
    ]


async def test_approval_without_event_call_is_left_pending() -> None:
    stream = ChunkStream(
        [
            sse(ev("approval", {"approval_id": "ap-1", "type": "generic", "summary": "s"}), "1"),
            sse(ev("end", {"outcome": "ok"}), "2"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway, event_call=None)

    chunks = await harness.run()

    assert gateway.approvals == []
    assert "Awaiting approval: s" in chunks[-1]


async def test_reconnects_once_with_after_when_stream_ends_without_end_event() -> None:
    first = ChunkStream(
        [sse(ev("delta", {"text": "part one"}), "10"), sse(ev("delta", {"text": ", "}), "11")]
    )
    second = ChunkStream(
        [sse(ev("delta", {"text": "part two"}), "12"), sse(ev("end", {"outcome": "ok"}), "13")]
    )
    gateway = FakeGateway([first, second])
    harness = Harness(gateway, show_timeline=False)

    chunks = await harness.run()

    assert "".join(chunks) == "part one, part two"
    events_requests = [r for r in gateway.requests if r.url.path.endswith("/events")]
    assert len(events_requests) == 2
    assert "after" not in events_requests[0].url.params
    assert events_requests[1].url.params["after"] == "11"
    assert events_requests[1].headers["Last-Event-ID"] == "11"
    assert gateway.paths("POST") == [f"POST /api/v2/sessions/{SESSION}/messages"]


async def test_reconnects_after_transport_error_and_gives_up_after_second_drop() -> None:
    first = ChunkStream([sse(ev("delta", {"text": "a"}), "1")], fail_after=True)
    second = ChunkStream([sse(ev("delta", {"text": "b"}), "2")], fail_after=True)
    gateway = FakeGateway([first, second])
    harness = Harness(gateway, show_timeline=False)

    chunks = await harness.run()

    assert "".join(chunks) == "ab"
    events_requests = [r for r in gateway.requests if r.url.path.endswith("/events")]
    assert [r.url.params.get("after") for r in events_requests] == [None, "1"]
    assert harness.statuses()[-1] == ("The event stream ended before the agent finished.", True)
    assert f"POST /api/v2/sessions/{SESSION}/cancel" in gateway.paths("POST")


async def test_client_stop_cancels_the_run() -> None:
    blocker = asyncio.Event()
    stream = ChunkStream([sse(ev("delta", {"text": "partial"}), "1")], block_after=blocker)
    gateway = FakeGateway([stream])
    harness = Harness(gateway)

    generator = harness.generator()
    assert await generator.__anext__() == "partial"
    await generator.aclose()
    blocker.set()

    assert gateway.paths("POST")[-1] == f"POST /api/v2/sessions/{SESSION}/cancel"


async def test_failed_stop_is_visible_and_still_attempted_without_run_id() -> None:
    blocker = asyncio.Event()
    stream = ChunkStream([sse(ev("delta", {"text": "partial"}), "1")], block_after=blocker)
    gateway = FakeGateway([stream], message_run_id=None, cancel_status=500)
    harness = Harness(gateway, show_timeline=False)

    generator = harness.generator()
    assert await generator.__anext__() == "partial"
    await generator.aclose()
    blocker.set()

    assert f"POST /api/v2/sessions/{SESSION}/cancel" in gateway.paths("POST")
    assert harness.statuses()[-1] == (
        "Stop did not reach the agent. The run may still be active.",
        True,
    )


async def test_completed_run_is_not_cancelled_on_close() -> None:
    stream = ChunkStream(
        [sse(ev("delta", {"text": "x"}), "1"), sse(ev("end", {"outcome": "ok"}), "2")]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway, show_timeline=False)

    await harness.run()

    assert all("/cancel" not in path for path in gateway.paths())


async def test_events_from_other_runs_are_ignored_but_notifications_pass() -> None:
    stream = ChunkStream(
        [
            sse(ev("delta", {"text": "mine"}), "1"),
            sse(ev("delta", {"text": "theirs"}, run="run-other"), "2"),
            sse(ev("end", {"outcome": "ok"}, run="run-other"), "3"),
            sse(
                ev(
                    "notification",
                    {"level": "warn", "title": "Spread", "body": "widened"},
                    run="run-other",
                ),
                "4",
            ),
            sse(ev("job", {"job_id": "j1", "kind": "cron", "status": "finished"}, run=None), "5"),
            sse(ev("end", {"outcome": "ok"}), "6"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway)

    chunks = await harness.run()

    assert chunks[0] == "mine"
    assert all("theirs" not in chunk for chunk in chunks)
    notifications = [e for e in harness.emitted if e["type"] == "notification"]
    assert notifications == [
        {"type": "notification", "data": {"type": "warning", "content": "Spread: widened"}}
    ]
    assert "Task update: cron j1 finished" in chunks[-1]


async def test_decision_card_uses_catalog_labels_and_adds_no_tool_row() -> None:
    payload = {
        "verdict": "buy",
        "entry": 2301.5,
        "reasons": ["hour break"],
    }
    labels = {
        "label.result.decision": "القرار",
        "label.result.decision.verdict": "الحكم",
        "label.result.decision.entry": "الدخول",
        "label.result.decision.reasons": "الأسباب",
        "label.decision.buy": "شراء",
        "result.field": "الحقل",
        "result.value": "القيمة",
    }
    failed = ChunkStream(
        [
            sse(
                ev(
                    "structured",
                    {"type": "decision", "result_id": "res-d", "payload": payload},
                ),
                "1",
            ),
            sse(ev("end", {"outcome": "ok"}), "2"),
        ]
    )
    gateway = FakeGateway([failed], html_status=500, labels=labels)
    harness = Harness(gateway, show_timeline=False)
    await harness.run()
    messages = [e for e in harness.emitted if e["type"] == "message"]
    content = str(messages[0]["data"]["content"])  # type: ignore[index]
    assert "**القرار**" in content
    assert "| الدخول | 2301.5 |" in content
    assert "| شراء |" in content or "| الحكم | شراء |" in content
    assert "| entry |" not in content
    assert "| verdict |" not in content
    assert not [e for e in harness.emitted if e["type"] == "embeds"]
    assert all("run_trading_kernel" not in description for description, _done in harness.statuses())

    shown = ChunkStream(
        [
            sse(
                ev(
                    "structured",
                    {"type": "decision", "result_id": "res-d", "payload": payload},
                ),
                "1",
            ),
            sse(ev("end", {"outcome": "ok"}), "2"),
        ]
    )
    html = "<div>القرار</div>"
    gateway = FakeGateway([shown], html=html, labels=labels)
    harness = Harness(gateway, show_timeline=False)
    await harness.run()
    embeds = [e for e in harness.emitted if e["type"] == "embeds"]
    assert embeds == [{"type": "embeds", "data": {"embeds": [html], "replace": True}}]
    assert not [e for e in harness.emitted if e["type"] == "message"]
    assert all("run_trading_kernel" not in description for description, _done in harness.statuses())


async def test_structured_falls_back_to_markdown_table_when_html_unavailable() -> None:
    stream = ChunkStream(
        [
            sse(
                ev(
                    "structured",
                    {
                        "type": "risk",
                        "result_id": "res-2",
                        "payload": {"risk_pct": 1.0, "blockers": [{"gate": "spread"}]},
                    },
                ),
                "1",
            ),
            sse(ev("end", {"outcome": "ok"}), "2"),
        ]
    )
    gateway = FakeGateway([stream], html_status=500)
    harness = Harness(gateway, show_timeline=False)

    await harness.run()

    messages = [e for e in harness.emitted if e["type"] == "message"]
    assert len(messages) == 1
    content = str(messages[0]["data"]["content"])  # type: ignore[index]
    assert "**Result: risk**" in content
    assert "| Field | Value |" in content
    assert "| risk_pct | 1.0 |" in content
    assert '| blockers | [{"gate": "spread"}] |' in content
    assert not [e for e in harness.emitted if e["type"] == "embeds"]


async def test_structured_falls_back_when_embeds_event_is_rejected() -> None:
    stream = ChunkStream(
        [
            sse(ev("structured", {"type": "market", "result_id": "r", "payload": {"p": 1}}), "1"),
            sse(ev("end", {"outcome": "ok"}), "2"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway, show_timeline=False, emitter_fails_for={"embeds"})

    await harness.run()

    assert harness.types() == ["message", "status"]


async def test_artifacts_become_files_or_embeds() -> None:
    stream = ChunkStream(
        [
            sse(
                ev(
                    "artifact",
                    {
                        "artifact_id": "a1",
                        "mime": "image/png",
                        "url": "https://gw/artifacts/a1.png",
                        "title": "Chart",
                    },
                ),
                "1",
            ),
            sse(
                ev(
                    "artifact",
                    {
                        "artifact_id": "a2",
                        "mime": "text/html",
                        "url": "https://gw/chart-host?token=t",
                        "title": "Live chart",
                    },
                ),
                "2",
            ),
            sse(ev("end", {"outcome": "ok"}), "3"),
        ]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway, show_timeline=False)

    await harness.run()

    files = [e for e in harness.emitted if e["type"] == "files"]
    assert files == [
        {
            "type": "files",
            "data": {
                "files": [
                    {
                        "type": "image",
                        "url": "https://gw/artifacts/a1.png",
                        "name": "Chart",
                        "content_type": "image/png",
                    }
                ]
            },
        }
    ]
    embeds = [e for e in harness.emitted if e["type"] == "embeds"]
    assert embeds == [
        {"type": "embeds", "data": {"embeds": ["https://gw/chart-host?token=t"], "replace": True}}
    ]


async def test_labels_are_fetched_per_locale_and_cached() -> None:
    def make_stream() -> ChunkStream:
        return ChunkStream(
            [
                sse(ev("state", {"state": "working"}), "1"),
                sse(ev("end", {"outcome": "ok"}), "2"),
            ]
        )

    gateway = FakeGateway(
        [make_stream(), make_stream(), make_stream()],
        labels={"state.working": "Crunching numbers", "outcome.ok": "All set"},
    )
    harness = Harness(gateway, show_timeline=False)

    await harness.run()
    await harness.run()
    await harness.run(metadata=harness.metadata(variables={"{{USER_LANGUAGE}}": "ar-BH"}))

    assert gateway.labels_calls == 2
    label_requests = [r for r in gateway.requests if r.url.path == "/api/v2/labels"]
    assert [r.url.params["locale"] for r in label_requests] == ["en", "ar-BH"]
    assert harness.statuses()[0] == ("Crunching numbers", False)
    assert harness.statuses()[1] == ("All set", True)
    message_requests = [r for r in gateway.requests if r.url.path.endswith("/messages")]
    assert json.loads(message_requests[-1].content)["locale"] == "ar-BH"


async def test_timeline_is_omitted_when_disabled() -> None:
    stream = ChunkStream(
        [
            sse(ev("tool", {"event": "started", "name": "t", "call_id": "c"}), "1"),
            sse(ev("delta", {"text": "ok"}), "2"),
            sse(ev("end", {"outcome": "ok"}), "3"),
        ]
    )
    harness = Harness(FakeGateway([stream]), show_timeline=False)

    assert await harness.run() == ["ok"]


async def test_selected_chat_model_is_forwarded() -> None:
    stream = ChunkStream(
        [sse(ev("delta", {"text": "ok"}), "1"), sse(ev("end", {"outcome": "ok"}), "2")]
    )
    gateway = FakeGateway([stream])
    harness = Harness(gateway)
    body = harness.body()
    body["model"] = "mokli.google/gemini-test"

    assert await harness.run(body) == ["ok"]
    message = next(request for request in gateway.requests if request.url.path.endswith("/messages"))
    assert json.loads(message.content)["model"] == "google/gemini-test"


async def test_background_tasks_do_not_reach_the_agent() -> None:
    gateway = FakeGateway([])
    harness = Harness(gateway)

    chunks = await harness.run(
        harness.body("What is the gold price today?"),
        harness.metadata(task="title_generation"),
    )

    assert json.loads("".join(chunks)) == {"title": "What is the gold price today?"}
    assert gateway.requests == []


async def test_gateway_http_error_is_reported_as_status_and_text() -> None:
    gateway = FakeGateway([])
    gateway.sessions.clear()

    async def failing(request: httpx.Request) -> httpx.Response:
        gateway.requests.append(request)
        if request.url.path == "/api/v2/labels":
            return httpx.Response(200, json={})
        return httpx.Response(503, json={"error": {"code": "down"}})

    harness = Harness(gateway)
    harness.pipe.transport = httpx.MockTransport(failing)

    chunks = await harness.run()

    assert chunks == ["\n\nThe agent gateway is unreachable."]
    assert harness.statuses() == [("The agent gateway is unreachable.", True)]
    assert all("/cancel" not in r.url.path for r in gateway.requests)


def test_pipes_manifest_and_valves_defaults() -> None:
    pipe = pipe_mod.Pipe()
    assert pipe.pipes() == [{"id": "mokli", "name": "Mokli"}]


def test_pipes_lists_models_chosen_for_the_agent(monkeypatch) -> None:
    def fake_get(*_args: object, **_kwargs: object) -> object:
        class Response:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"models": [{"id": "google/gemini-test", "name": "google/gemini-test"}]}

        return Response()

    monkeypatch.setattr(pipe_mod.httpx, "get", fake_get)
    pipe = pipe_mod.Pipe()
    pipe.valves.GATEWAY_TOKEN = "nbat_test"
    assert pipe.pipes() == [
        {"id": "mokli", "name": "Mokli"},
        {"id": "google/gemini-test", "name": "google/gemini-test"},
    ]
    assert pipe._requested_model({"model": "mokli.google/gemini-test"}) == "google/gemini-test"
    assert pipe._requested_model({"model": "mokli.mokli"}) is None
    assert pipe._requested_model({"model": "mokli"}) is None
    assert pipe._requested_model({"model": "openai/gpt-4.1"}) == "openai/gpt-4.1"
    assert pipe._requested_model({"model": "other.google/gemini-test"}) == "google/gemini-test"
    valves = pipe.Valves()
    assert valves.GATEWAY_URL == "http://127.0.0.1:8766"
    assert valves.GATEWAY_TOKEN == ""
    assert valves.DEFAULT_LOCALE == "en"
    assert valves.SHOW_TIMELINE is True
    assert valves.REQUEST_TIMEOUT == 30.0


def test_pipe_copies_stay_identical() -> None:
    root = Path(__file__).resolve().parents[2]
    deploy = (root / "deploy/mokliui/functions/mokli_pipe.py").read_bytes()
    fork = (root / "mokli-ui/functions/mokli_pipe.py").read_bytes()
    assert deploy == fork


def test_local_chat_reuses_the_mokliui_session_id() -> None:
    pipe = pipe_mod.Pipe()
    metadata = {"chat_id": "local", "session_id": "ws1"}
    assert pipe._session_id(metadata, {}) == "owui-ws1"
    assert pipe._session_id(metadata, {}) == "owui-ws1"


async def test_missing_run_id_is_not_posted_again_after_a_dropped_stream() -> None:
    first = ChunkStream([sse(ev("delta", {"text": "a"}), "1")], fail_after=True)
    second = ChunkStream([sse(ev("end", {"outcome": "ok"}), "2")])
    gateway = FakeGateway([first, second], message_run_id=None)
    harness = Harness(gateway, show_timeline=False)

    chunks = await harness.run()

    assert "".join(chunks) == "a"
    posts = [request for request in gateway.requests if request.url.path.endswith("/messages")]
    assert len(posts) == 1


def test_unknown_model_is_not_reported_as_gateway_unreachable() -> None:
    request = httpx.Request("POST", "http://gateway/api/v2/sessions/s/messages")
    response = httpx.Response(
        400,
        json={"error": {"code": "unknown_model", "details": {"model": "missing-model"}}},
        request=request,
    )
    exc = httpx.HTTPStatusError("bad request", request=request, response=response)
    text = pipe_mod.Pipe._gateway_failure_text(exc, pipe_mod._Turn("s", "en", {}))
    assert text == "Unknown model: missing-model"


def test_activity_projection_matches_real_events() -> None:
    assert pipe_mod.project_activity([]) == []
    assert pipe_mod.project_activity([ev("state", {"state": "working", "phase": "thinking"})]) == []
    one = pipe_mod.project_activity([
        ev("tool", {"event": "started", "name": "get_gold_quote", "call_id": "c1",
                    "display": "يفحص سعر الذهب الحالي…"}),
    ])
    assert len(one) == 1
    assert one[0]["label"] == "يفحص سعر الذهب الحالي…"
    assert "get_gold_quote" not in str(one[0]["label"])
    several = pipe_mod.project_activity([
        ev("tool", {"event": "started", "name": "get_gold_quote", "call_id": "c1",
                    "display": "يفحص سعر الذهب الحالي…"}),
        ev("tool", {"event": "finished", "name": "get_gold_quote", "call_id": "c1",
                    "display": "تم فحص سعر الذهب"}),
        ev("subagent", {"event": "started", "id": "sa", "role": "Risk Officer"}),
        ev("tool", {"event": "started", "name": "not_a_real_extra", "call_id": "c2"}),
    ])
    assert [step["id"] for step in several] == ["c1", "sa", "c2"]
    assert several[0]["label"] == "تم فحص سعر الذهب"
    assert several[1]["label"] == "Risk Officer"
    assert several[2]["label"] == "Working on a step"
    assert pipe_mod.format_duration_ms(200) == "200 ms"
    assert pipe_mod.format_duration_ms(3700) == "3.7 s"
    failed = pipe_mod.project_activity([
        ev("tool", {"event": "started", "name": "get_gold_quote", "call_id": "c9",
                    "display": "يفحص سعر الذهب الحالي…"}),
        ev("tool", {"event": "failed", "name": "get_gold_quote", "call_id": "c9",
                    "display": "تعذر الحصول على سعر الذهب", "duration_ms": 200}),
    ])
    assert len(failed) == 1
    assert failed[0]["failed"] is True
    assert failed[0]["label"] == "تعذر الحصول على سعر الذهب"
    line = pipe_mod.activity_line(failed)
    assert line == "تعذر الحصول على سعر الذهب"
    assert "✓" not in line
    visible_ids = {step["id"] for step in several}
    event_ids = {"c1", "sa", "c2"}
    assert visible_ids == event_ids
    quiet = pipe_mod.project_activity([ev("state", {"state": "working"})])
    assert all(step.get("kind") != "retry" for step in quiet)
    retry = pipe_mod.project_activity([
        ev("retry", {"state": "waiting", "attempt": 2, "error_kind": "connection"}),
        ev("retry", {"state": "recovered", "attempt": 2, "error_kind": "connection"}),
        ev("retry", {"state": "cleared", "attempt": 4, "error_kind": "server"}),
    ])
    assert [step["id"] for step in retry] == ["retry-2", "fallback"]
    assert retry[0]["label"] == "Retry succeeded"
    assert retry[0]["done"] is True
    assert retry[0]["failed"] is False
    assert retry[1]["label"] == "Using another provider"
    cancelled_retry = pipe_mod.project_activity([
        ev("retry", {"state": "waiting", "attempt": 1, "error_kind": "connection"}),
        ev("retry", {"state": "cancelled", "attempt": 1, "error_kind": "cancelled"}),
    ])
    assert len(cancelled_retry) == 1
    assert cancelled_retry[0]["id"] == "retry-1"
    assert cancelled_retry[0]["label"] == "Retry cancelled"
    assert cancelled_retry[0]["done"] is True
    assert cancelled_retry[0]["failed"] is True
    assert "✓" not in pipe_mod.activity_line(cancelled_retry)
    assert "✓" not in pipe_mod.activity_line([
        {"label": "Retry failed", "done": True, "failed": True},
    ])
    agents = pipe_mod.project_activity([
        ev("subagent", {"event": "started", "id": "technical", "role": "Technical Analyst"}),
        ev("subagent", {"event": "finished", "id": "technical", "role": "Technical Analyst",
                        "duration_ms": 3700}),
        ev("subagent", {"event": "started", "id": "risk", "role": "Risk Officer"}),
        ev("subagent", {"event": "failed", "id": "risk", "role": "Risk Officer",
                        "duration_ms": 200}),
    ])
    assert [step["id"] for step in agents] == ["technical", "risk"]
    assert agents[0]["done"] is True and agents[0]["failed"] is not True
    assert agents[1]["failed"] is True
    assert "✓" not in pipe_mod.activity_line([agents[1]])
    assert pipe_mod.activity_line(agents) == "Technical Analyst ✓ · Risk Officer"
    displayed = pipe_mod.project_activity([
        ev("subagent", {
            "event": "started",
            "id": "technical",
            "role": "Technical Analyst",
            "display": "يراجع الهيكل السعري…",
        }),
        ev("subagent", {
            "event": "finished",
            "id": "technical",
            "role": "Technical Analyst",
            "display": "اكتملت مراجعة الهيكل",
        }),
    ])
    assert displayed[0]["label"] == "اكتملت مراجعة الهيكل"
    assert displayed[0]["technical"] == "Technical Analyst"
    assert "Technical Analyst" not in pipe_mod.activity_line(displayed)
    assert pipe_mod.activity_line([
        {"label": "يفحص سعر الذهب الحالي…", "done": False},
    ]) == "يفحص سعر الذهب الحالي…"
    assert pipe_mod.activity_line([
        {"label": "يشغّل محرك التحليل", "done": False},
    ]) == "يشغّل محرك التحليل …"
    assert pipe_mod.activity_line([
        {"label": "تم فحص سعر الذهب ✓", "done": True},
    ]) == "تم فحص سعر الذهب ✓"


async def test_timeline_keeps_one_detail_row_per_real_operation() -> None:
    stream = ChunkStream(
        [
            sse(ev("tool", {
                "event": "started",
                "name": "get_gold_quote",
                "call_id": "c1",
                "display": "يفحص سعر الذهب الحالي…",
                "arguments": '{"symbol":"XAUUSD"}',
                "source": "metaapi",
            }), "1"),
            sse(ev("tool", {
                "event": "finished",
                "name": "get_gold_quote",
                "call_id": "c1",
                "display": "تم فحص سعر الذهب",
                "summary": "bid 2401",
                "duration_ms": 200,
            }), "2"),
            sse(ev("tool", {
                "event": "started",
                "name": "get_gate_report",
                "call_id": "c2",
                "display": "يتحقق من شروط القرار…",
            }), "3"),
            sse(ev("tool", {
                "event": "failed",
                "name": "get_gate_report",
                "call_id": "c2",
                "display": "تعذر فحص شروط القرار",
                "summary": "feed down",
                "duration_ms": 3700,
            }), "4"),
            sse(ev("subagent", {
                "event": "started",
                "id": "risk",
                "role": "Risk Officer",
                "display": "يراجع المخاطر…",
            }), "5"),
            sse(ev("subagent", {
                "event": "finished",
                "id": "risk",
                "role": "Risk Officer",
                "display": "اكتملت مراجعة المخاطر",
                "summary": "STANCE: wait",
                "duration_ms": 3700,
            }), "6"),
            sse(ev("retry", {"state": "waiting", "attempt": 1, "error_kind": "connection"}), "7"),
            sse(ev("retry", {"state": "recovered", "attempt": 1, "error_kind": "connection"}), "8"),
            sse(ev("end", {"run": RUN, "outcome": "ok"}), "9"),
        ]
    )
    harness = Harness(FakeGateway([stream]))
    chunks = await harness.run()
    timeline = chunks[-1]
    rows = [line[2:] for line in timeline.splitlines() if line.startswith("- ")]
    assert rows == [
        'get_gold_quote · finished · 200 ms · {"symbol":"XAUUSD"} · metaapi · bid 2401',
        "get_gate_report · failed · 3.7 s · feed down",
        "Risk Officer · finished · 3.7 s · STANCE: wait",
        "retry · recovered · 1 · connection",
    ]
    descriptions = [text for text, _done in harness.statuses()]
    assert "get_gold_quote" not in descriptions[0]
    assert descriptions[-1] == (
        "تم فحص سعر الذهب ✓ · تعذر فحص شروط القرار · اكتملت مراجعة المخاطر ✓ · Retry succeeded ✓"
    )
