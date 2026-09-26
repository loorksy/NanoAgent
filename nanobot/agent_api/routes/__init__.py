"""Route registration for ``/api/v2`` and ``/ws/v2``."""

from __future__ import annotations

from aiohttp import web

from nanobot.agent_api.routes import (
    approvals,
    connect,
    devices,
    jobs,
    labels,
    log,
    me,
    recommendations,
    results,
    sessions,
    settings,
    ws,
)

API_PREFIX = "/api/v2"
WS_PATH = "/ws/v2"


def setup_routes(app: web.Application) -> None:
    router = app.router
    me.register(router, API_PREFIX)
    sessions.register(router, API_PREFIX)
    approvals.register(router, API_PREFIX)
    jobs.register(router, API_PREFIX)
    results.register(router, API_PREFIX)
    labels.register(router, API_PREFIX)
    recommendations.register(router, API_PREFIX)
    connect.register(router, API_PREFIX)
    log.register(router, API_PREFIX)
    devices.register(router, API_PREFIX)
    settings.register(router, API_PREFIX)
    ws.register(router, WS_PATH)
