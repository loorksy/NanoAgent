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
    apk = _VERSION_FILE.parent / "nanoagent.apk"
    if apk.is_file():
        payload["apk_url"] = "/api/v2/distribution/apk"
    if _VERSION_FILE.is_file():
        raw: object = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            mapping = cast(dict[str, object], raw)
            for key in ("version", "min_version", "apk_url", "notes_key"):
                value = mapping.get(key)
                if isinstance(value, str) and (key != "apk_url" or value.strip()):
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
        "usage": _usage_snapshot(),
    })


def capabilities_view(
    *,
    dream: bool,
    audio: bool,
    image: bool,
    web: bool,
) -> dict[str, object]:
    """Operator-facing capability flags. No secrets."""
    return {
        "items": [
            {"key": "dream", "enabled": dream},
            {"key": "audio", "enabled": audio},
            {"key": "image", "enabled": image},
            {"key": "web", "enabled": web},
        ],
        "trading": ["fast_backtest", "propose_strategy"],
    }


def system_view(
    *,
    timezone: str,
    host: str,
    port: int,
    enabled: bool,
    version: str,
) -> dict[str, object]:
    """Listener and timezone summary. The bootstrap token stays out of this document."""
    return {
        "timezone": timezone,
        "host": host,
        "port": port,
        "enabled": enabled,
        "version": version,
    }


def public_models(providers: dict[str, object], default_model: str) -> dict[str, object]:
    """Provider list for Settings → Models. Never includes API keys."""
    rows: list[dict[str, object]] = []
    for name in sorted(providers):
        raw = providers[name]
        if not isinstance(raw, dict):
            continue
        fields = cast(dict[str, object], raw)
        key = fields.get("api_key")
        base = fields.get("api_base")
        rows.append({
            "name": name,
            "configured": bool(isinstance(key, str) and key.strip()),
            "api_base": base if isinstance(base, str) else "",
        })
    return {
        "default_model": default_model,
        "pipe_model": "nanoagent.nanoagent",
        "providers": rows,
    }


def _usage_snapshot() -> dict[str, object]:
    try:
        from nanobot.llm_usage import llm_usage_payload

        payload = llm_usage_payload(days=7)
    except Exception:
        return {}
    if isinstance(payload, dict):
        return cast(dict[str, object], payload)
    return {}


async def capabilities(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.config.loader import load_config

    config = load_config()
    return ok(
        capabilities_view(
            dream=config.agents.defaults.dream.enabled,
            audio=config.transcription.enabled,
            image=bool(config.tools.image_generation.enabled),
            web=bool(config.tools.web.enable),
        )
    )


async def system_settings(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.config.loader import load_config

    config = load_config()
    api = config.agent_api
    return ok(
        system_view(
            timezone=config.agents.defaults.timezone,
            host=api.host,
            port=api.port,
            enabled=api.enabled,
            version=__version__,
        )
    )


async def chat_models(request: web.Request) -> web.Response:
    """Models chosen for the agent, so the chat picker can list them."""
    require_scope(request, "chat")
    from nanobot.api.chat_models import public_chat_models
    from nanobot.config.loader import load_config

    return ok({"models": public_chat_models(load_config())})


async def models_settings(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.config.loader import load_config

    config = load_config()
    dumped = cast(dict[str, object], config.providers.model_dump())
    return ok(public_models(dumped, config.agents.defaults.model))


async def distribution_apk(request: web.Request) -> web.Response:
    del request
    path = _VERSION_FILE.parent / "nanoagent.apk"
    if not path.is_file():
        from nanobot.agent_api.errors import ApiError

        raise ApiError(404, "apk_missing")
    return web.FileResponse(path)


async def distribution(request: web.Request) -> web.Response:
    return ok(distribution_document())


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/settings/overview", overview)
    router.add_get(f"{prefix}/chat/models", chat_models)
    router.add_get(f"{prefix}/settings/models", models_settings)
    router.add_get(f"{prefix}/settings/capabilities", capabilities)
    router.add_get(f"{prefix}/settings/system", system_settings)
    router.add_get(f"{prefix}/distribution/version", distribution)
    router.add_get(f"{prefix}/distribution/apk", distribution_apk)
