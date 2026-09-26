"""Sessions REST + SSE stream (``/api/v2/sessions``)."""

from __future__ import annotations

import asyncio
import json
from typing import cast

from aiohttp import web
from loguru import logger

from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import GatewayEvent, JsonObject
from nanobot.agent_api.routes._util import json_body, ok, optional_str, query_int
from nanobot.api.chat_models import canonical_chat_model_id
from nanobot.config.loader import load_config

SSE_KEEPALIVE_SECONDS = 15.0
MEDIA_SUBDIR = "agent_api"


def sse_frame(event: GatewayEvent) -> bytes:
    payload = json.dumps(event, ensure_ascii=False, default=str)
    return f"id: {event['id']}\nevent: {event['kind']}\ndata: {payload}\n\n".encode()


def _part_data_url(part: dict[str, object]) -> str | None:
    """SDK ``MessageContentPart`` → data URL (``url`` may already be one, or ``base64``+``mime``)."""
    if part.get("type") not in ("image", "audio"):
        return None
    url = part.get("url")
    if isinstance(url, str) and url.startswith("data:"):
        return url
    base64_payload = part.get("base64")
    mime = part.get("mime")
    if isinstance(base64_payload, str) and base64_payload and isinstance(mime, str) and mime:
        return f"data:{mime};base64,{base64_payload}"
    return None


def message_text(body: JsonObject) -> str:
    """Text from ``text`` / ``content`` or the ``text`` parts of ``parts``."""
    for field in ("text", "content"):
        value = body.get(field)
        if isinstance(value, str) and value.strip():
            return value
    parts = body.get("parts")
    if isinstance(parts, list):
        texts = [
            str(cast(dict[str, object], part).get("text") or "")
            for part in cast(list[object], parts)
            if isinstance(part, dict) and cast(dict[str, object], part).get("type") == "text"
        ]
        return "\n".join(text for text in texts if text.strip())
    return ""


def media_paths(body: JsonObject) -> list[str]:
    """Persist base64 data URLs (image/audio) the same way the OpenAI-compatible API does."""
    from nanobot.api.server import _save_base64_data_url
    from nanobot.config.paths import get_media_dir

    urls: list[str] = []
    for field in ("image", "audio"):
        value = body.get(field)
        if isinstance(value, str) and value.startswith("data:"):
            urls.append(value)
    parts = body.get("parts")
    if isinstance(parts, list):
        for raw in cast(list[object], parts):
            if isinstance(raw, dict):
                data_url = _part_data_url(cast(dict[str, object], raw))
                if data_url is not None:
                    urls.append(data_url)
    media = body.get("media")
    if isinstance(media, list):
        urls.extend(
            item for item in cast(list[object], media)
            if isinstance(item, str) and item.startswith("data:")
        )
    # Open WebUI pipe shape: [{"type": "image", "url": "data:..."}]
    attachments = body.get("attachments")
    if isinstance(attachments, list):
        for raw in cast(list[object], attachments):
            if not isinstance(raw, dict):
                continue
            url = cast(dict[str, object], raw).get("url")
            if isinstance(url, str) and url.startswith("data:"):
                urls.append(url)
    if not urls:
        return []
    media_dir = get_media_dir(MEDIA_SUBDIR)
    saved: list[str] = []
    for url in urls:
        path = _save_base64_data_url(url, media_dir)
        if path:
            saved.append(path)
    return saved


async def list_sessions(request: web.Request) -> web.Response:
    require_scope(request, "read")
    include_archived = request.query.get("archived") in ("1", "true")
    return ok({"sessions": services(request).sessions.list(include_archived=include_archived)})


async def create_session(request: web.Request) -> web.Response:
    require_scope(request, "chat")
    body = await json_body(request, optional=True)
    title = optional_str(body, "title") or ""
    session_id = optional_str(body, "id") or request.headers.get("X-NanoAgent-Session")
    record = services(request).sessions.create(title=title, session_id=session_id or None)
    return ok(record, status=201)


async def get_session(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    record = svc.sessions.get(request.match_info["id"])
    if record is None:
        raise ApiError(404, "session_not_found")
    return ok({**record, "state_detail": svc.hub.state.snapshot(record["id"])})


async def delete_session(request: web.Request) -> web.Response:
    require_scope(request, "control")
    removed = await services(request).sessions.delete(request.match_info["id"])
    if not removed:
        raise ApiError(404, "session_not_found")
    return ok({"deleted": True})


async def post_message(request: web.Request) -> web.Response:
    require_scope(request, "chat")
    svc = services(request)
    session_id = request.match_info["id"]
    body = await json_body(request)
    text = message_text(body)
    media = media_paths(body)
    if not text.strip() and not media:
        raise ApiError(400, "empty_message")
    in_flight = svc.sessions.busy_run(session_id)
    if in_flight:
        raise ApiError(409, "run_in_progress", details={"run": in_flight})
    if "model" in body:
        model = body.get("model")
        if model is not None and not isinstance(model, str):
            raise ApiError(400, "invalid_field", details={"field": "model"})
        try:
            selected = canonical_chat_model_id(load_config(), model)
        except ValueError as exc:
            raise ApiError(400, "unknown_model", details={"model": str(exc)}) from exc
        if selected is None:
            if not svc.sessions.clear_model(session_id):
                raise ApiError(500, "model_clear_failed", details={"session": session_id})
        elif not svc.sessions.use_model(session_id, selected):
            raise ApiError(400, "unknown_model", details={"model": selected})
    run_id = svc.sessions.submit(session_id, text, media=media)
    return ok({"run_id": run_id, "session": session_id}, status=202)


async def cancel_session(request: web.Request) -> web.Response:
    require_scope(request, "control")
    svc = services(request)
    session_id = request.match_info["id"]
    cancelled = await svc.sessions.cancel(session_id)
    return ok({"cancelled": cancelled, "state": svc.hub.state.snapshot(session_id)})


async def session_state(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    session_id = request.match_info["id"]
    snapshot = svc.hub.state.snapshot(session_id)
    return ok({
        **snapshot,
        "pending_approvals": [a["id"] for a in svc.approvals.pending_for_session(session_id)],
        "last_event_id": svc.event_log.last_id(session_id),
    })


async def timeline(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    after = request.query.get("after") or None
    limit = query_int(request, "limit", 500, maximum=5000)
    events = svc.sessions.timeline(request.match_info["id"], after=after)[:limit]
    return ok({"events": events})


async def events_stream(request: web.Request) -> web.StreamResponse:
    require_scope(request, "read")
    svc = services(request)
    session_id = request.match_info["id"]
    after = request.query.get("after") or request.headers.get("Last-Event-ID") or None
    until_end = request.query.get("until_end") in ("1", "true")
    keepalive = float(request.query.get("keepalive") or SSE_KEEPALIVE_SECONDS)

    subscription = svc.hub.subscribe(session_id)
    response = web.StreamResponse(
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    await response.prepare(request)
    last_id = after
    try:
        for event in svc.event_log.after(session_id, after):
            await response.write(sse_frame(event))
            last_id = event["id"]
            if until_end and event["kind"] == "end":
                return response
        await response.write(b": connected\n\n")
        while True:
            event = await subscription.get(timeout=keepalive)
            if event is None:
                await response.write(b": keepalive\n\n")
                continue
            if last_id is not None and event["id"] <= last_id:
                continue
            await response.write(sse_frame(event))
            last_id = event["id"]
            if until_end and event["kind"] == "end":
                break
    except (ConnectionResetError, asyncio.CancelledError):
        logger.debug("agent_api SSE client for {} disconnected", session_id)
    finally:
        subscription.close()
    return response


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/sessions", list_sessions)
    router.add_post(f"{prefix}/sessions", create_session)
    router.add_get(f"{prefix}/sessions/{{id}}", get_session)
    router.add_delete(f"{prefix}/sessions/{{id}}", delete_session)
    router.add_post(f"{prefix}/sessions/{{id}}/messages", post_message)
    router.add_post(f"{prefix}/sessions/{{id}}/cancel", cancel_session)
    router.add_get(f"{prefix}/sessions/{{id}}/state", session_state)
    router.add_get(f"{prefix}/sessions/{{id}}/timeline", timeline)
    router.add_get(f"{prefix}/sessions/{{id}}/events", events_stream)
