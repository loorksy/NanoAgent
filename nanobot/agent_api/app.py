"""Application factory and listener for the Agent API (``/api/v2`` + ``/ws/v2``).

``create_app`` wires every service around one ``AgentLoop``; ``AgentApiServer``
owns the aiohttp runner so the gateway can start/stop it alongside channels.
"""

from __future__ import annotations

import asyncio
import os
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web
from loguru import logger

from nanobot.agent_api.approvals import ApprovalRegistry
from nanobot.agent_api.auth import TOKEN_PREFIX, TokenStore, auth_middleware_factory
from nanobot.agent_api.config import AgentApiConfig
from nanobot.agent_api.context import SERVICES_KEY, AgentApiServices, ConnectionTracker
from nanobot.agent_api.db import Database, default_db_path
from nanobot.agent_api.devices import DeviceRegistry
from nanobot.agent_api.errors import ApiError, error_response
from nanobot.agent_api.event_log import EventLog
from nanobot.agent_api.hub import EventHub
from nanobot.agent_api.jobs import CronServiceLike, JobsService, SessionManagerLike
from nanobot.agent_api.push.base import PushProvider
from nanobot.agent_api.push.router import PushRouter
from nanobot.agent_api.results import ResultsStore
from nanobot.agent_api.routes import setup_routes
from nanobot.agent_api.sessions import AgentLoopLike, RuntimeEventBridge, SessionService
from nanobot.agent_api.tools.emit_result import register_emit_result_tool
from nanobot.events import AgentEvent

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
Subscribe = Callable[[Callable[[AgentEvent], None]], Callable[[], None]]
ADMIN_TOKEN_FILENAME = "admin_token"
MAINTENANCE_INTERVAL_SECONDS = 600.0
CLIENT_MAX_SIZE = 20 * 1024 * 1024

_BRIDGE_KEY = web.AppKey[RuntimeEventBridge]("agent_api_bridge")
_MAINTENANCE_KEY = web.AppKey["asyncio.Task[None]"]("agent_api_maintenance")
_ALLOWED_METHODS = "GET, POST, PUT, DELETE, OPTIONS"
_ALLOWED_HEADERS = "Authorization, Content-Type, Last-Event-ID, X-NanoAgent-Session"


# ---------------------------------------------------------------------------
# middlewares
# ---------------------------------------------------------------------------


@web.middleware
async def error_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except ApiError as exc:
        return exc.response()
    except web.HTTPException as exc:
        if exc.status >= 400:
            return error_response(exc.status, exc.reason.lower().replace(" ", "_"))
        raise
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("agent_api unhandled error on {} {}", request.method, request.path)
        return error_response(500, "internal_error")


def cors_middleware_factory(origins: list[str]) -> Callable[..., Awaitable[web.StreamResponse]]:
    allow_all = "*" in origins
    allowed = {origin.rstrip("/") for origin in origins}

    def _origin_for(request: web.Request) -> str | None:
        origin = request.headers.get("Origin")
        if not origin:
            return None
        if allow_all:
            return origin
        return origin if origin.rstrip("/") in allowed else None

    @web.middleware
    async def middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
        origin = _origin_for(request)
        if request.method == "OPTIONS":
            response: web.StreamResponse = web.Response(status=204)
        else:
            response = await handler(request)
        if origin is not None:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = _ALLOWED_METHODS
            response.headers["Access-Control-Allow-Headers"] = _ALLOWED_HEADERS
            response.headers["Access-Control-Expose-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
            response.headers["Vary"] = "Origin"
        return response

    return middleware


# ---------------------------------------------------------------------------
# bootstrap token
# ---------------------------------------------------------------------------


def admin_token_path(workspace: Path) -> Path:
    return Path(workspace) / "agent_api" / ADMIN_TOKEN_FILENAME


def resolve_bootstrap_token(config: AgentApiConfig, workspace: Path) -> str:
    """Config value wins; otherwise reuse/generate ``<workspace>/agent_api/admin_token``."""
    if config.bootstrap_token.strip():
        return config.bootstrap_token.strip()
    path = admin_token_path(workspace)
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if existing:
        return existing
    token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


# ---------------------------------------------------------------------------
# factory
# ---------------------------------------------------------------------------


@dataclass
class AgentApiDeps:
    """Optional collaborators the gateway can hand to :func:`create_app`."""

    cron: CronServiceLike | None = None
    session_manager: SessionManagerLike | None = None
    subscribe_runtime_events: Subscribe | None = None
    push_providers: list[PushProvider] | None = None
    timezone: str | None = None
    config_path: Path | None = None
    db_path: Path | None = None


def build_services(
    agent: AgentLoopLike,
    config: AgentApiConfig,
    workspace: Path,
    deps: AgentApiDeps | None = None,
) -> AgentApiServices:
    deps = deps or AgentApiDeps()
    db = Database(deps.db_path or default_db_path(workspace))
    event_log = EventLog(
        db,
        retention_days=config.event_retention_days,
        max_events_per_session=config.max_events_per_session,
    )
    hub = EventHub(event_log)
    approvals = ApprovalRegistry(db, hub)
    sessions = SessionService(
        agent, hub, approvals, db, request_timeout=config.request_timeout_seconds,
    )
    tokens = TokenStore(
        db,
        bootstrap_token=resolve_bootstrap_token(config, workspace),
        default_ttl_seconds=config.token_ttl_seconds,
    )
    devices = DeviceRegistry(db)
    connections = ConnectionTracker()
    push = PushRouter(hub, devices, deps.push_providers, connected=connections.any_connected)
    jobs = JobsService(deps.cron, deps.session_manager, timezone=deps.timezone)
    return AgentApiServices(
        config=config,
        db=db,
        event_log=event_log,
        hub=hub,
        sessions=sessions,
        approvals=approvals,
        jobs=jobs,
        results=ResultsStore(db),
        tokens=tokens,
        devices=devices,
        push=push,
        connections=connections,
        config_path=deps.config_path,
    )


def create_app(
    agent: AgentLoopLike,
    config: AgentApiConfig,
    workspace: Path,
    deps: AgentApiDeps | None = None,
    *,
    services: AgentApiServices | None = None,
) -> web.Application:
    """Build the aiohttp application; ``services`` may be injected for tests."""
    deps = deps or AgentApiDeps()
    svc = services or build_services(agent, config, workspace, deps)
    app = web.Application(
        client_max_size=CLIENT_MAX_SIZE,
        middlewares=[
            cors_middleware_factory(config.cors_origins),
            error_middleware,
            auth_middleware_factory(svc.tokens),
        ],
    )
    app[SERVICES_KEY] = svc
    setup_routes(app)

    registry = getattr(agent, "tools", None)
    if registry is not None and hasattr(registry, "register"):
        try:
            register_emit_result_tool(registry, svc.results, svc.hub)
        except Exception:
            logger.debug("agent_api emit_result tool registration skipped", exc_info=True)

    bridge = RuntimeEventBridge(svc.hub)
    if deps.subscribe_runtime_events is not None:
        bridge.attach(deps.subscribe_runtime_events)
    app[_BRIDGE_KEY] = bridge

    async def _on_startup(_app: web.Application) -> None:
        svc.push.attach()
        svc.approvals.expire_due()
        _app[_MAINTENANCE_KEY] = asyncio.create_task(
            _maintenance(svc), name="agent-api-maintenance",
        )

    async def _on_cleanup(_app: web.Application) -> None:
        task = _app.get(_MAINTENANCE_KEY)
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        svc.push.detach()
        await svc.push.wait_idle()
        bridge.detach()
        for record in svc.sessions.list():
            if svc.sessions.active_run(record["id"]) is not None:
                await svc.sessions.cancel(record["id"])
        svc.db.close()

    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    return app


async def _maintenance(svc: AgentApiServices) -> None:
    while True:
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)
        try:
            for record in svc.approvals.expire_due():
                logger.info("agent_api approval {} expired", record["id"])
            svc.tokens.purge_expired()
            pruned = await asyncio.to_thread(svc.event_log.prune)
            if pruned:
                logger.debug("agent_api pruned {} events", pruned)
        except Exception:
            logger.exception("agent_api maintenance failed")


# ---------------------------------------------------------------------------
# listener
# ---------------------------------------------------------------------------


class AgentApiServer:
    """Own the ``AppRunner`` / ``TCPSite`` pair for the Agent API listener."""

    def __init__(self, app: web.Application, *, host: str, port: int) -> None:
        self.app = app
        self.host = host
        self.port = port
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def services(self) -> AgentApiServices:
        return self.app[SERVICES_KEY]

    @property
    def url(self) -> str:
        host = "127.0.0.1" if self.host in ("", "0.0.0.0") else self.host
        return f"http://{host}:{self.port}"

    async def start(self) -> None:
        if self._runner is not None:
            return
        runner = web.AppRunner(self.app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self._runner = runner
        self._site = site
        bound = _bound_address(site)
        if bound is not None and self.port == 0:
            self.port = bound[1]
        logger.info("Agent API listening on {}/api/v2 (ws: /ws/v2)", self.url)

    async def stop(self) -> None:
        runner = self._runner
        self._runner = None
        self._site = None
        if runner is not None:
            await runner.cleanup()

    async def serve_forever(self) -> None:
        await self.start()
        try:
            await asyncio.Event().wait()
        finally:
            await self.stop()


def _bound_address(site: web.TCPSite) -> tuple[str, int] | None:
    server = getattr(site, "_server", None)
    sockets = getattr(server, "sockets", None)
    if not sockets:
        return None
    try:
        host, port = sockets[0].getsockname()[:2]
    except (OSError, ValueError, TypeError):
        return None
    return str(host), int(port)


def build_server(
    agent: AgentLoopLike,
    config: AgentApiConfig,
    workspace: Path,
    deps: AgentApiDeps | None = None,
) -> AgentApiServer:
    app = create_app(agent, config, workspace, deps)
    return AgentApiServer(app, host=config.host, port=config.port)


__all__ = [
    "AgentApiDeps",
    "AgentApiServer",
    "build_server",
    "build_services",
    "create_app",
    "resolve_bootstrap_token",
]
