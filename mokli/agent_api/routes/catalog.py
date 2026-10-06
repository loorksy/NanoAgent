"""Workspace catalog: agent skills and the live tool registry."""

from __future__ import annotations

import asyncio

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.catalog import set_skill_enabled, skill_rows, tool_rows
from mokli.agent_api.context import services
from mokli.agent_api.errors import ApiError
from mokli.agent_api.routes._util import json_body, ok
from mokli.surface.skills_api import SkillManagementError


async def get_skills(request: web.Request) -> web.Response:
    require_scope(request, "read")
    path = services(request).config_path
    return ok(await asyncio.to_thread(skill_rows, path))


async def put_skill(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        raise ApiError(400, "invalid_field", details={"field": "enabled"})
    name = request.match_info["name"]
    path = services(request).config_path

    def _save() -> dict[str, object]:
        try:
            return set_skill_enabled(name, enabled=enabled, config_path=path)
        except SkillManagementError as exc:
            raise ApiError(exc.status, "invalid_field", details={"field": "name"}) from exc

    return ok(await asyncio.to_thread(_save))


async def get_tools(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok(await asyncio.to_thread(tool_rows))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/workspace/skills", get_skills)
    router.add_put(f"{prefix}/workspace/skills/{{name}}", put_skill)
    router.add_get(f"{prefix}/workspace/tools", get_tools)
