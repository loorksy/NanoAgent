"""Provider connect routes (``/api/v2/settings/providers`` and Claude Code)."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import web

from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.provider_settings import (
    claude_callback,
    claude_connect,
    create_custom_provider,
    provider_document,
    provider_models_document,
    provider_oauth,
    save_api_provider,
    save_claude_token,
    save_provider_models,
)
from nanobot.agent_api.routes._util import json_body, ok
from nanobot.webui.settings_services import WebUIOAuthFlowRegistry


def _flows(request: web.Request) -> WebUIOAuthFlowRegistry:
    current = services(request).oauth_flows
    if isinstance(current, WebUIOAuthFlowRegistry):
        return current
    created = WebUIOAuthFlowRegistry()
    services(request).oauth_flows = created
    return created


async def list_providers(request: web.Request) -> web.Response:
    require_scope(request, "read")
    path = services(request).config_path
    return ok(await asyncio.to_thread(provider_document, path))


async def create_provider(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    return ok(await asyncio.to_thread(create_custom_provider, body, config_path=path))


async def update_provider(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    name = request.match_info["name"]
    return ok(await asyncio.to_thread(save_api_provider, name, body, config_path=path))


async def list_provider_models(request: web.Request) -> web.Response:
    require_scope(request, "read")
    path = services(request).config_path
    name = request.match_info["name"]
    query = request.query.get("q", "")
    return ok(
        await asyncio.to_thread(
            provider_models_document,
            name,
            config_path=path,
            query=query,
        )
    )


async def update_provider_models(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    name = request.match_info["name"]
    return ok(await asyncio.to_thread(save_provider_models, name, body, config_path=path))


async def oauth_provider(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    name = request.match_info["name"]
    flows = _flows(request)

    def _run() -> dict[str, Any]:
        return provider_oauth(name, body, flows, config_path=path)

    return ok(await asyncio.to_thread(_run))


async def claude_status(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.webui.claude_code_oauth import public_status

    return ok(public_status())


async def claude_save(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    return ok(await asyncio.to_thread(save_claude_token, body, config_path=path))


async def claude_start(request: web.Request) -> web.Response:
    require_scope(request, "control")
    flows = _flows(request)
    return ok(await asyncio.to_thread(claude_connect, flows))


async def claude_finish(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    path = services(request).config_path
    flows = _flows(request)
    return ok(await asyncio.to_thread(claude_callback, body, flows, config_path=path))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/settings/providers", list_providers)
    router.add_post(f"{prefix}/settings/providers", create_provider)
    router.add_put(f"{prefix}/settings/providers/{{name}}", update_provider)
    router.add_get(f"{prefix}/settings/providers/{{name}}/models", list_provider_models)
    router.add_put(f"{prefix}/settings/providers/{{name}}/models", update_provider_models)
    router.add_post(f"{prefix}/settings/providers/{{name}}/oauth", oauth_provider)
    router.add_get(f"{prefix}/settings/claude-code", claude_status)
    router.add_post(f"{prefix}/settings/claude-code", claude_save)
    router.add_post(f"{prefix}/settings/claude-code/connect", claude_start)
    router.add_post(f"{prefix}/settings/claude-code/callback", claude_finish)
