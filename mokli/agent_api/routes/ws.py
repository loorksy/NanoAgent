"""WebSocket multiplex (``/ws/v2``): one socket per client, many sessions.

Client → server frames (JSON objects; ``type`` is accepted as an alias of ``op``,
matching ``@mokli/sdk``):

* ``{"op": "subscribe", "session": "...", "after": "<event_id>"?}``
* ``{"op": "unsubscribe", "session": "..."}``
* ``{"op": "send", "session": "...", "text": "...", "parts": [...]?, "media": [...]?}``
* ``{"op": "cancel", "session": "..."}``
* ``{"op": "approve", "approval_id": "...", "decision": "confirm"|"cancel"}``
* ``{"op": "ping"}``

Every frame may carry ``"req"`` / ``"request_id"`` (client correlation id) which is
echoed back on the matching ack/error.

Server → client frames:

* ``{"type": "hello", "client_id", "scopes", "server_time"}``
* ``{"type": "event", "event": <GatewayEvent>}`` — same shape as SSE ``data``
* ``{"type": "ack", "op", "req"?, "request_id"?, ...result}``
* ``{"type": "error", "op"?, "req"?, "request_id"?, "error": {"code", "message_key", "details"}}``
* ``{"type": "pong", "req"?, "request_id"?}``
"""

from __future__ import annotations

import asyncio
import json
from typing import cast

from aiohttp import WSMsgType, web
from loguru import logger

from mokli.agent_api.auth import Principal, principal_of, require_any_scope, require_scope
from mokli.agent_api.context import AgentApiServices, services
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import GatewayEvent, JsonObject, now_ms
from mokli.agent_api.hub import Subscription
from mokli.agent_api.routes.sessions import media_paths, message_text, optional_locale

WS_HEARTBEAT_SECONDS = 20.0
_MAX_FRAME_BYTES = 1 << 20
_OUTGOING_LIMIT = 4000


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _correlation(req: object) -> JsonObject:
    """Echo the client's correlation id under both accepted names."""
    return {"req": req, "request_id": req}


class WsClient:
    """Per-connection state: subscriptions and the serialized outgoing queue."""

    def __init__(
        self,
        ws: web.WebSocketResponse,
        svc: AgentApiServices,
        principal: Principal,
        request: web.Request,
    ) -> None:
        self.ws = ws
        self.svc = svc
        self.principal = principal
        self.request = request
        self._subs: dict[str, tuple[Subscription, asyncio.Task[None]]] = {}
        self._outgoing: asyncio.Queue[str | None] = asyncio.Queue(maxsize=_OUTGOING_LIMIT)
        self._writer: asyncio.Task[None] | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        self._writer = asyncio.create_task(self._write_loop(), name="agent-api-ws-writer")

    async def close(self) -> None:
        for session in list(self._subs):
            self._unsubscribe(session)
        if self._writer is not None:
            await self._outgoing.put(None)
            try:
                await asyncio.wait_for(self._writer, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                self._writer.cancel()

    async def _write_loop(self) -> None:
        while True:
            frame = await self._outgoing.get()
            if frame is None:
                return
            if self.ws.closed:
                return
            try:
                await self.ws.send_str(frame)
            except (ConnectionResetError, RuntimeError):
                return

    def enqueue(self, frame: JsonObject) -> None:
        try:
            self._outgoing.put_nowait(_dumps(frame))
        except asyncio.QueueFull:
            logger.warning("agent_api ws client {} too slow; dropping frame", self.principal["client_id"])

    # -- subscriptions -------------------------------------------------------

    def _forward(self, session: str, sub: Subscription) -> asyncio.Task[None]:
        async def loop() -> None:
            while not sub.closed:
                event = await sub.get()
                if event is None:
                    continue
                self.enqueue({"type": "event", "event": event})

        return asyncio.create_task(loop(), name=f"agent-api-ws-forward:{session}")

    def subscribe(self, session: str, after: str | None) -> int:
        if session in self._subs:
            self._unsubscribe(session)
        sub = self.svc.hub.subscribe(session)
        replayed: list[GatewayEvent] = self.svc.event_log.after(session, after) if after else []
        for event in replayed:
            self.enqueue({"type": "event", "event": event})
        self._subs[session] = (sub, self._forward(session, sub))
        return len(replayed)

    def _unsubscribe(self, session: str) -> bool:
        found = self._subs.pop(session, None)
        if found is None:
            return False
        sub, task = found
        sub.close()
        task.cancel()
        return True

    # -- ops -----------------------------------------------------------------

    async def handle(self, frame: JsonObject) -> None:
        op = frame.get("op", frame.get("type"))
        req = frame.get("req", frame.get("request_id"))
        if not isinstance(op, str):
            self._error(None, req, ApiError(400, "invalid_frame", details={"field": "op"}))
            return
        try:
            result = await self._dispatch(op, frame)
        except ApiError as exc:
            self._error(op, req, exc)
            return
        except Exception as exc:
            logger.exception("agent_api ws op {} failed", op)
            self._error(op, req, ApiError(500, "internal_error", details={"error": str(exc)}))
            return
        if op == "ping":
            self.enqueue({"type": "pong", **_correlation(req), "server_time": now_ms()})
            return
        ack: JsonObject = {"type": "ack", "op": op, **_correlation(req)}
        ack.update(result)
        self.enqueue(ack)

    def _error(self, op: str | None, req: object, exc: ApiError) -> None:
        body: JsonObject = {"type": "error", "op": op, **_correlation(req)}
        body.update(cast(JsonObject, exc.envelope()))
        self.enqueue(body)

    def _session(self, frame: JsonObject) -> str:
        session = frame.get("session")
        if not isinstance(session, str) or not session.strip():
            raise ApiError(400, "invalid_frame", details={"field": "session"})
        return session

    async def _dispatch(self, op: str, frame: JsonObject) -> JsonObject:
        if op == "ping":
            return {}
        if op == "subscribe":
            require_scope(self.request, "read")
            session = self._session(frame)
            after = frame.get("after")
            replayed = self.subscribe(session, after if isinstance(after, str) else None)
            return {
                "session": session,
                "replayed": replayed,
                "state": self.svc.hub.state.snapshot(session),
            }
        if op == "unsubscribe":
            session = self._session(frame)
            return {"session": session, "removed": self._unsubscribe(session)}
        if op == "send":
            require_scope(self.request, "chat")
            session = self._session(frame)
            text = message_text(frame)
            media = media_paths(frame)
            self.svc.sessions.ensure(session)
            if session not in self._subs:
                self.subscribe(session, None)
            run_id = self.svc.sessions.submit(
                session, text, media=media, locale=optional_locale(frame)
            )
            return {"session": session, "run_id": run_id}
        if op == "cancel":
            require_any_scope(self.request, "chat", "control")
            session = self._session(frame)
            cancelled = await self.svc.sessions.cancel(session)
            return {"session": session, "cancelled": cancelled}
        if op == "approve":
            require_scope(self.request, "approve")
            approval_id = frame.get("approval_id")
            decision = frame.get("decision")
            if not isinstance(approval_id, str) or not approval_id:
                raise ApiError(400, "invalid_frame", details={"field": "approval_id"})
            if decision not in ("confirm", "cancel"):
                raise ApiError(400, "invalid_frame", details={"field": "decision"})
            record = await self.svc.approvals.decide(approval_id, decision)
            return {"approval": record}
        raise ApiError(400, "unknown_op", details={"op": op})


async def websocket(request: web.Request) -> web.StreamResponse:
    principal = principal_of(request)
    svc = services(request)
    ws = web.WebSocketResponse(heartbeat=WS_HEARTBEAT_SECONDS, max_msg_size=_MAX_FRAME_BYTES)
    await ws.prepare(request)

    client = WsClient(ws, svc, principal, request)
    client.start()
    svc.connections.connected(principal["client_id"])
    client.enqueue({
        "type": "hello",
        "client_id": principal["client_id"],
        "scopes": list(principal["scopes"]),
        "server_time": now_ms(),
    })
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    raw: object = json.loads(msg.data)
                except json.JSONDecodeError:
                    client.enqueue({
                        "type": "error",
                        **cast(JsonObject, ApiError(400, "invalid_json").envelope()),
                    })
                    continue
                if not isinstance(raw, dict):
                    client.enqueue({
                        "type": "error",
                        **cast(JsonObject, ApiError(400, "invalid_frame").envelope()),
                    })
                    continue
                await client.handle(cast(JsonObject, raw))
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                break
            elif msg.type == WSMsgType.ERROR:
                logger.debug("agent_api ws error: {}", ws.exception())
                break
    finally:
        svc.connections.disconnected(principal["client_id"])
        await client.close()
    return ws


def register(router: web.UrlDispatcher, path: str) -> None:
    router.add_get(path, websocket)
