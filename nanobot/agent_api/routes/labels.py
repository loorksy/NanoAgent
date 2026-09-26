"""Label catalog (``GET /api/v2/labels?locale=``)."""

from __future__ import annotations

from aiohttp import web

from nanobot.agent_api.auth import principal_of
from nanobot.agent_api.labels import (
    SUPPORTED_LOCALES,
    catalog,
    normalize_locale,
    text_direction,
)
from nanobot.agent_api.routes._util import ok


def resolve_locale(request: web.Request) -> str:
    """Query param wins, then the client's stored locale, then English."""
    requested = request.query.get("locale")
    if requested:
        return normalize_locale(requested)
    try:
        return normalize_locale(principal_of(request)["locale"])
    except Exception:
        return "en"


async def labels(request: web.Request) -> web.Response:
    locale = resolve_locale(request)
    prefix = request.query.get("prefix") or ""
    entries = catalog(locale)
    if prefix:
        entries = {key: value for key, value in entries.items() if key.startswith(prefix)}
    return ok({
        "locale": locale,
        "dir": text_direction(locale),
        "supported": list(SUPPORTED_LOCALES),
        "labels": entries,
    })


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/labels", labels)
