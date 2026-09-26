"""Structured results (``/api/v2/results``): JSON and rendered HTML."""

from __future__ import annotations

from aiohttp import web

from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.render.html import render_result_html
from nanobot.agent_api.results import RESULT_TYPES
from nanobot.agent_api.routes._util import ok, query_int
from nanobot.agent_api.routes.labels import resolve_locale


async def list_results(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    session = request.query.get("session") or None
    limit = query_int(request, "limit", 50, maximum=500)
    result_type = request.query.get("type") or None
    if result_type is not None and result_type not in RESULT_TYPES:
        raise ApiError(400, "invalid_query", details={"param": "type"})
    records = svc.results.list(session=session, limit=limit)
    if result_type is not None:
        records = [record for record in records if record["type"] == result_type]
    return ok({"results": records, "types": list(RESULT_TYPES)})


async def get_result(request: web.Request) -> web.Response:
    require_scope(request, "read")
    record = services(request).results.get(request.match_info["id"])
    if record is None:
        raise ApiError(404, "result_not_found")
    return ok(record)


async def result_html(request: web.Request) -> web.Response:
    require_scope(request, "read")
    record = services(request).results.get(request.match_info["id"])
    if record is None:
        raise ApiError(404, "result_not_found")
    html = render_result_html(record, resolve_locale(request))
    return web.Response(
        text=html,
        content_type="text/html",
        charset="utf-8",
        headers={"Cache-Control": "private, max-age=60"},
    )


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/results", list_results)
    router.add_get(f"{prefix}/results/{{id}}", get_result)
    router.add_get(f"{prefix}/results/{{id}}/html", result_html)
