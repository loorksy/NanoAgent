"""Client identity (``GET /api/v2/me``) and public health (``GET /api/v2/health``)."""

from __future__ import annotations

from aiohttp import web

from mokli import __version__
from mokli.agent_api.auth import principal_of
from mokli.agent_api.context import services
from mokli.agent_api.labels import text_direction
from mokli.agent_api.routes._util import ok


async def me(request: web.Request) -> web.Response:
    principal = principal_of(request)
    svc = services(request)
    return ok({
        "client_id": principal["client_id"],
        "kind": principal["kind"],
        "scopes": list(principal["scopes"]),
        "label": principal["label"],
        "locale": principal["locale"],
        "dir": text_direction(principal["locale"]),
        "server": {
            "version": __version__,
            "api": "v2",
            "token_ttl_seconds": svc.config.token_ttl_seconds,
        },
    })


async def health(request: web.Request) -> web.Response:
    svc = services(request)
    return ok({
        "ok": True,
        "version": __version__,
        "api": "v2",
        "sessions_running": sum(
            1 for record in svc.sessions.list() if record["state"] == "working"
        ),
    })


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/me", me)
    router.add_get(f"{prefix}/health", health)
    router.add_get("/health", health)
