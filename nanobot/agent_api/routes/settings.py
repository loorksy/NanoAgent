"""Settings aliases the Open WebUI fork calls (``/api/v2/settings/*``).

Risk and permissions stay on the connect handlers. This module adds the
overview and distribution documents those screens need.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from aiohttp import web

from nanobot import __version__
from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.routes._util import ok

_VERSION_FILE = Path(__file__).resolve().parents[3] / "mobile" / "version.json"


def distribution_document() -> dict[str, object]:
    payload: dict[str, object] = {
        "version": "0.1.0",
        "min_version": "0.1.0",
        "apk_url": "",
        "server_version": __version__,
        "notes_key": "distribution.android",
    }
    if _VERSION_FILE.is_file():
        raw: object = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            mapping = cast(dict[str, object], raw)
            for key in ("version", "min_version", "apk_url", "notes_key"):
                value = mapping.get(key)
                if isinstance(value, str):
                    payload[key] = value
    return payload


async def overview(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.trading.config import load_trading_config
    from nanobot.trading.runtime_state import get_runtime_store

    cfg = load_trading_config()
    return ok({
        "product": "NanoAgent",
        "api": "v2",
        "server_version": __version__,
        "distribution": distribution_document(),
        "runtime": get_runtime_store().snapshot().to_dict(),
        "brokers": {
            "oanda": {
                "configured": cfg.oanda_configured,
                "env": cfg.oanda_env,
                "account_id": cfg.oanda_account_id or "",
            },
            "metaapi": cfg.public_metaapi(),
        },
    })


async def distribution(request: web.Request) -> web.Response:
    return ok(distribution_document())


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/settings/overview", overview)
    router.add_get(f"{prefix}/distribution/version", distribution)
