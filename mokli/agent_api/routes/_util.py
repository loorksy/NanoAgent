"""Shared request helpers for route modules."""

from __future__ import annotations

from typing import cast

from aiohttp import web

from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import JsonObject


async def json_body(request: web.Request, *, optional: bool = False) -> JsonObject:
    if optional and not request.can_read_body:
        return {}
    try:
        raw: object = await request.json()
    except Exception as exc:
        raise ApiError(400, "invalid_json") from exc
    if not isinstance(raw, dict):
        raise ApiError(400, "invalid_json", details={"expected": "object"})
    return cast(JsonObject, raw)


def require_str(body: JsonObject, field: str, *, allow_empty: bool = False) -> str:
    value = body.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ApiError(400, "invalid_field", details={"field": field})
    return value


def optional_str(body: JsonObject, field: str) -> str | None:
    value = body.get(field)
    return value if isinstance(value, str) else None


def optional_int(body: JsonObject, field: str) -> int | None:
    value = body.get(field)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def query_int(request: web.Request, name: str, default: int, *, maximum: int | None = None) -> int:
    raw = request.query.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(400, "invalid_query", details={"param": name}) from exc
    if maximum is not None:
        value = min(value, maximum)
    return value


def ok(payload: object, status: int = 200) -> web.Response:
    return web.json_response(payload, status=status, dumps=_dumps)


def _dumps(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)
