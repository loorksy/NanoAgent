"""Operator sections: performance, briefing, and token burn.

These are the three surfaces the old client had as dedicated pages. The
documents come from the same trading and usage stores the gateway already
keeps; this module only exposes them on ``/api/v2``.
"""

from __future__ import annotations

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.routes._util import ok, query_int


async def performance(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from mokli.mokli.trading_api import performance_document

    return ok(performance_document())


async def briefing(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from mokli.mokli.trading_api import briefing_document

    locale = request.query.get("locale") or None
    return ok(briefing_document(locale))


async def usage(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from mokli.llm_usage import llm_usage_payload

    days = query_int(request, "days", 30, maximum=371)
    return ok(llm_usage_payload(days=days))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/performance", performance)
    router.add_get(f"{prefix}/briefing", briefing)
    router.add_get(f"{prefix}/usage", usage)
