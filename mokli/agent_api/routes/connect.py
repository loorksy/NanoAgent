"""Connection / risk / permissions / runtime controls (``/api/v2/connect``, ``/api/v2/control``).

Write paths reuse the Mokli trading-risk actions so both surfaces persist
through the same validation, derivation and audit code (04 §4, 08).
"""

from __future__ import annotations

import asyncio
import json
from typing import Literal, cast

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.context import services
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import JsonObject, notification_data
from mokli.agent_api.routes._util import json_body, ok, optional_str, require_str

RuntimeField = Literal["paused", "kill_switch", "paper_mode"]
CONTROL_SESSION = "system"


def _risk_error(exc: BaseException) -> ApiError:
    status = getattr(exc, "status", 400)
    message = getattr(exc, "message", str(exc))
    return ApiError(
        status if isinstance(status, int) else 400,
        "trading_risk_error",
        details={"message": str(message)},
    )


async def _risk_action(
    request: web.Request,
    action: str,
    query: dict[str, list[str]],
    *,
    who: str | None = None,
) -> JsonObject:
    from mokli.surface.trading_risk_api import TradingRiskError, trading_risk_action

    svc = services(request)
    try:
        result = await asyncio.to_thread(
            trading_risk_action,
            action,
            query,
            config_path=svc.config_path,
            who=who,
        )
    except TradingRiskError as exc:
        raise _risk_error(exc) from exc
    return cast(JsonObject, result)


def _risk_payload(request: web.Request) -> JsonObject:
    from mokli.surface.trading_risk_api import trading_risk_payload

    return cast(JsonObject, trading_risk_payload(config_path=services(request).config_path))


def _permissions_payload(request: web.Request) -> JsonObject:
    from mokli.surface.trading_risk_api import mt5_permissions_payload

    return cast(JsonObject, mt5_permissions_payload(config_path=services(request).config_path))


def _runtime_state() -> JsonObject:
    from mokli.trading.runtime_state import get_runtime_store

    return cast(JsonObject, get_runtime_store().snapshot().to_dict())


def _brokers() -> JsonObject:
    from mokli.trading.config import load_trading_config

    cfg = load_trading_config()
    return {
        "oanda": {
            "configured": cfg.oanda_configured,
            "env": cfg.oanda_env,
            "account_id": cfg.oanda_account_id or "",
        },
        "mt5": cast(JsonObject, cfg.public_mt5()),
    }


def _risk_state() -> JsonObject:
    from mokli.trading.risk_state import get_risk_store

    state = get_risk_store().snapshot()
    return {
        "consecutive_losses": state.consecutive_losses,
        "cooldown_until_ms": state.cooldown_until_ms,
        "cooldown_reason": state.cooldown_reason,
        "daily_pnl_pct": state.daily_pnl_pct,
        "open_positions": state.open_positions,
        "emergency_lock": state.emergency_lock,
        "news_day": state.news_day,
        "holiday": state.holiday,
        "feature_toggles": dict(state.feature_toggles),
    }


def _connect_snapshot(request: web.Request) -> JsonObject:
    risk = _risk_payload(request)
    permissions = _permissions_payload(request)
    return {
        "brokers": _brokers(),
        "runtime_state": _runtime_state(),
        "risk_state": _risk_state(),
        "risk": {
            "profile": risk.get("profile"),
            "values": risk.get("values"),
            "groups": risk.get("groups"),
            "toggles": risk.get("toggles"),
            "locked_toggles": risk.get("locked_toggles"),
        },
        "mt5_permissions": {
            "permissions": permissions.get("permissions"),
            "effective": permissions.get("effective"),
            "levels": permissions.get("levels"),
            "actions": permissions.get("actions"),
            "sessions": permissions.get("sessions"),
        },
    }


# -- handlers -------------------------------------------------------------------


async def get_connect(request: web.Request) -> web.Response:
    require_scope(request, "read")
    snapshot = await asyncio.to_thread(_connect_snapshot, request)
    return ok(snapshot)


async def get_risk(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok(await asyncio.to_thread(_risk_payload, request))


async def put_risk_profile(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    name = require_str(body, "name").strip().lower()
    return ok(await _risk_action(request, "profile", {"name": [name]}))


async def put_risk_field(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    if "value" not in body:
        raise ApiError(400, "invalid_field", details={"field": "value"})
    field = request.match_info["field"]
    query: dict[str, list[str]] = {
        "values": [json.dumps({field: body["value"]}, default=str)],
    }
    if body.get("derive", True):
        query["derive"] = ["1"]
    return ok(await _risk_action(request, "update", query))


async def put_risk(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    query: dict[str, list[str]] = {}
    values = body.get("values")
    toggles = body.get("toggles")
    if isinstance(values, dict):
        query["values"] = [json.dumps(values, default=str)]
    if isinstance(toggles, dict):
        query["toggles"] = [json.dumps(toggles, default=str)]
    if not query:
        raise ApiError(400, "invalid_field", details={"field": "values|toggles"})
    if body.get("derive", True):
        query["derive"] = ["1"]
    return ok(await _risk_action(request, "update", query))


async def get_permissions(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok(await asyncio.to_thread(_permissions_payload, request))


async def put_permissions(request: web.Request) -> web.Response:
    principal = require_scope(request, "control")
    body = await json_body(request)
    permissions = body.get("permissions", body)
    if not isinstance(permissions, dict):
        raise ApiError(400, "invalid_field", details={"field": "permissions"})
    who = optional_str(body, "who") or f"{principal['kind']}:{principal['client_id']}"
    result = await _risk_action(
        request,
        "mt5-permissions-update",
        {"permissions": [json.dumps(permissions, default=str)]},
        who=who,
    )
    return ok(result)


def _set_runtime(field: RuntimeField, enabled: bool) -> JsonObject:
    from mokli.trading.runtime_state import get_runtime_store

    state = get_runtime_store().update(**{field: enabled})
    from mokli.trading.policy import invalidate_live_cache

    invalidate_live_cache()
    return cast(JsonObject, state.to_dict())


async def _control(
    request: web.Request,
    field: RuntimeField,
    *,
    default: bool,
    label_key: str,
) -> web.Response:
    principal = require_scope(request, "control")
    body = await json_body(request, optional=True)
    enabled = body.get("enabled", default)
    if not isinstance(enabled, bool):
        raise ApiError(400, "invalid_field", details={"field": "enabled"})
    state = await asyncio.to_thread(_set_runtime, field, enabled)
    svc = services(request)
    svc.hub.publish(
        CONTROL_SESSION,
        "notification",
        notification_data(
            "warning" if enabled and field != "paper_mode" else "info",
            label_key,
            f"{label_key}.{'on' if enabled else 'off'}",
            args={"by": principal["client_id"], "field": field, "enabled": enabled},
        ),
    )
    return ok({"runtime_state": state, "changed": field, "enabled": enabled})


async def control_kill(request: web.Request) -> web.Response:
    return await _control(request, "kill_switch", default=True, label_key="control.kill_switch")


async def control_pause(request: web.Request) -> web.Response:
    return await _control(request, "paused", default=True, label_key="control.pause")


async def control_resume(request: web.Request) -> web.Response:
    principal = require_scope(request, "control")
    state = await asyncio.to_thread(_set_runtime, "paused", False)
    services(request).hub.publish(
        CONTROL_SESSION,
        "notification",
        notification_data(
            "info",
            "control.pause",
            "control.pause.off",
            args={"by": principal["client_id"], "field": "paused", "enabled": False},
        ),
    )
    return ok({"runtime_state": state, "changed": "paused", "enabled": False})


async def control_paper_mode(request: web.Request) -> web.Response:
    return await _control(request, "paper_mode", default=True, label_key="control.paper_mode")


async def get_control(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok({"runtime_state": await asyncio.to_thread(_runtime_state)})


async def get_channels(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from mokli.agent_api.messaging import channel_rows

    path = services(request).config_path
    if path is None:
        raise ApiError(500, "config_unavailable")
    rows = await asyncio.to_thread(channel_rows, path)
    return ok({"channels": rows})


async def post_telegram(request: web.Request) -> web.Response:
    require_scope(request, "control")
    from mokli.agent_api.messaging import channel_rows, enable_channel, save_telegram_token

    path = services(request).config_path
    if path is None:
        raise ApiError(500, "config_unavailable")
    body = await json_body(request)
    token = require_str(body, "token").strip()
    await asyncio.to_thread(save_telegram_token, path, token)
    requires_restart = await enable_channel(path, "telegram")
    rows = await asyncio.to_thread(channel_rows, path)
    row = next(item for item in rows if item["name"] == "telegram")
    row["saved"] = True
    row["requires_restart"] = requires_restart
    return ok(row)


async def post_whatsapp(request: web.Request) -> web.Response:
    require_scope(request, "control")
    from mokli.agent_api.messaging import (
        channel_rows,
        connector,
        enable_channel,
        public_connect_payload,
    )
    from mokli.channels.connect import ChannelConnectError

    path = services(request).config_path
    if path is None:
        raise ApiError(500, "config_unavailable")
    body = await json_body(request)
    action = require_str(body, "action").strip()
    if action not in {"start", "poll", "cancel"}:
        raise ApiError(400, "invalid_field", details={"field": "action"})
    query: dict[str, list[str]] = {}
    session_id = optional_str(body, "session_id")
    if session_id:
        query["session_id"] = [session_id.strip()]
    if body.get("force") is True:
        query["force"] = ["true"]
    try:
        payload = await connector("whatsapp").handle(action, query)
    except ChannelConnectError as exc:
        raise ApiError(exc.status, "channel_connect_error", details={"message": exc.message}) from exc
    if not isinstance(payload, dict):
        raise ApiError(500, "channel_connect_error")
    public = public_connect_payload(payload)
    if public["status"] == "succeeded":
        public["requires_restart"] = await enable_channel(path, "whatsapp")
    rows = await asyncio.to_thread(channel_rows, path)
    public["channel"] = next((item for item in rows if item["name"] == "whatsapp"), {})
    return ok(public)


async def get_mt5_status(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from mokli.surface.trading_mt5_api import TradingMt5Error, trading_mt5_action

    path = services(request).config_path
    try:
        payload = await trading_mt5_action("status", {}, config_path=path)
    except TradingMt5Error as exc:
        raise ApiError(exc.status, "mt5_connect_error", details={"message": exc.message}) from exc
    return ok(payload)


async def post_mt5(request: web.Request) -> web.Response:
    require_scope(request, "control")
    from mokli.surface.trading_mt5_api import TradingMt5Error, trading_mt5_action

    path = services(request).config_path
    body = await json_body(request)
    query: dict[str, list[str]] = {}
    for key in ("login", "password", "server", "host", "port"):
        value = body.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            query[key] = [text]
    try:
        payload = await trading_mt5_action("update", query, config_path=path)
    except TradingMt5Error as exc:
        raise ApiError(exc.status, "mt5_connect_error", details={"message": exc.message}) from exc
    return ok(payload)


async def post_mt5_disconnect(request: web.Request) -> web.Response:
    require_scope(request, "control")
    from mokli.surface.trading_mt5_api import TradingMt5Error, trading_mt5_action

    path = services(request).config_path
    try:
        payload = await trading_mt5_action("disconnect", {}, config_path=path)
    except TradingMt5Error as exc:
        raise ApiError(exc.status, "mt5_connect_error", details={"message": exc.message}) from exc
    return ok(payload)


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/connect/channels", get_channels)
    router.add_post(f"{prefix}/connect/channels/telegram", post_telegram)
    router.add_post(f"{prefix}/connect/channels/whatsapp", post_whatsapp)
    router.add_get(f"{prefix}/connect", get_connect)
    router.add_get(f"{prefix}/connect/risk", get_risk)
    router.add_put(f"{prefix}/connect/risk", put_risk)
    router.add_put(f"{prefix}/connect/risk-profile", put_risk_profile)
    router.add_put(f"{prefix}/connect/risk/{{field}}", put_risk_field)
    router.add_get(f"{prefix}/connect/mt5/status", get_mt5_status)
    router.add_post(f"{prefix}/connect/mt5", post_mt5)
    router.add_post(f"{prefix}/connect/mt5/disconnect", post_mt5_disconnect)
    router.add_get(f"{prefix}/connect/mt5/permissions", get_permissions)
    router.add_put(f"{prefix}/connect/mt5/permissions", put_permissions)
    router.add_get(f"{prefix}/control", get_control)
    router.add_post(f"{prefix}/control/kill", control_kill)
    router.add_post(f"{prefix}/control/pause", control_pause)
    router.add_post(f"{prefix}/control/resume", control_resume)
    router.add_post(f"{prefix}/control/paper-mode", control_paper_mode)


__all__ = ["CONTROL_SESSION", "register"]
