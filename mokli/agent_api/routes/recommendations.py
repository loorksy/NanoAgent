"""Recommendations (``/api/v2/recommendations``): live plan and archive.

Reads the trading recommendation store directly; ``session`` query values are
public session ids and are mapped to internal keys with :func:`session_key_for`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import JsonObject, session_id_for_key, session_key_for
from mokli.agent_api.routes._util import ok, query_int

Row = dict[str, object]
_MAX_SCAN = 2000


def _public(row: Row) -> JsonObject:
    out: JsonObject = dict(row)
    key = out.pop("session_key", None)
    out["session"] = session_id_for_key(key) if isinstance(key, str) else None
    return out


def _store() -> tuple[
    Callable[[str | None], Row | None],
    Callable[[int], list[Row]],
    Callable[[str], Row | None],
]:
    from mokli.trading.recommendations import store

    return (
        cast(Callable[[str | None], Row | None], store.latest_live_recommendation),
        cast(Callable[[int], list[Row]], store.list_recommendations),
        cast(Callable[[str], Row | None], store.get_recommendation),
    )


def _int_query(request: web.Request, name: str) -> int | None:
    raw = request.query.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ApiError(400, "invalid_query", details={"param": name}) from exc


async def live(request: web.Request) -> web.Response:
    require_scope(request, "read")
    latest_live, _list, _get = _store()
    session = request.query.get("session") or None
    if session is None:
        raise ApiError(400, "invalid_query", details={"param": "session", "required": True})
    row = latest_live(session_key_for(session))
    return ok({"live": _public(row) if row is not None else None, "session": session})


async def list_all(request: web.Request) -> web.Response:
    require_scope(request, "read")
    _live, list_recent, _get = _store()
    limit = query_int(request, "limit", 50, maximum=500)
    since = _int_query(request, "from")
    until = _int_query(request, "to")
    session = request.query.get("session") or None
    status = request.query.get("status") or None
    key = session_key_for(session) if session else None

    rows = list_recent(_MAX_SCAN if (since or until or session or status) else limit)
    selected: list[JsonObject] = []
    for row in rows:
        created = row.get("created_at")
        created_int = created if isinstance(created, int) else 0
        if since is not None and created_int < since:
            continue
        if until is not None and created_int > until:
            continue
        if key is not None and row.get("session_key") != key:
            continue
        if status is not None and row.get("status") != status:
            continue
        selected.append(_public(row))
        if len(selected) >= limit:
            break
    return ok({"recommendations": selected, "count": len(selected)})


async def get_one(request: web.Request) -> web.Response:
    require_scope(request, "read")
    _live, _list, get_recommendation = _store()
    row = get_recommendation(request.match_info["id"])
    if row is None:
        raise ApiError(404, "recommendation_not_found")
    return ok(_public(row))


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/recommendations", list_all)
    router.add_get(f"{prefix}/recommendations/live", live)
    router.add_get(f"{prefix}/recommendations/{{id}}", get_one)
