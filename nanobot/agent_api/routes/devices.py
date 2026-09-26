"""Devices and pairing (``/api/v2/devices``).

* ``POST /devices/pair`` is public: redeem a one-time pairing code (shown as a
  QR by the operator UI) for a long-lived ``device`` token.
* ``POST /devices/pairing-codes`` (admin) mints codes.
* ``POST /devices`` registers/refreshes a push token for the calling client.
* ``GET /devices`` lists the caller's devices (admin sees all).
* ``DELETE /devices/{id}`` revokes a device.
* ``POST /devices/revoke-client`` (admin) revokes a client and all its devices.
"""

from __future__ import annotations

from aiohttp import web

from nanobot.agent_api.auth import is_admin, principal_of, require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.devices import Platform, public_device
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.labels import normalize_locale
from nanobot.agent_api.routes._util import (
    json_body,
    ok,
    optional_int,
    optional_str,
    require_str,
)

PLATFORMS: tuple[Platform, ...] = ("android", "ios", "web")
PAIRING_CODE_TTL_SECONDS = 300
PAIRING_CODE_MAX_TTL_SECONDS = 3600


def _platform(value: object) -> Platform:
    if value in PLATFORMS:
        return value
    raise ApiError(400, "invalid_field", details={"field": "platform", "allowed": list(PLATFORMS)})


async def register_device(request: web.Request) -> web.Response:
    principal = require_scope(request, "push")
    svc = services(request)
    body = await json_body(request)
    platform = _platform(body.get("platform"))
    push_token = require_str(body, "push_token")
    label = optional_str(body, "label") or principal["label"]
    locale = normalize_locale(optional_str(body, "locale") or principal["locale"])
    device = svc.devices.register(
        client_id=principal["client_id"],
        platform=platform,
        push_token=push_token,
        label=label,
        locale=locale,
    )
    return ok(public_device(device), status=201)


async def list_devices(request: web.Request) -> web.Response:
    principal = require_scope(request, "read")
    svc = services(request)
    include_revoked = request.query.get("revoked") in ("1", "true")
    client_id = None if is_admin(principal) else principal["client_id"]
    devices = svc.devices.list(client_id=client_id, include_revoked=include_revoked)
    return ok({"devices": [public_device(device) for device in devices]})


async def delete_device(request: web.Request) -> web.Response:
    principal = require_scope(request, "push")
    svc = services(request)
    device = svc.devices.get(request.match_info["id"])
    if device is None:
        raise ApiError(404, "device_not_found")
    if device["client_id"] != principal["client_id"] and not is_admin(principal):
        raise ApiError(403, "forbidden")
    svc.devices.revoke(device["id"])
    return ok({"deleted": True, "id": device["id"]})


async def create_pairing_code(request: web.Request) -> web.Response:
    principal = principal_of(request)
    if not is_admin(principal):
        raise ApiError(403, "forbidden", "auth.missing_scope", {"scope": "admin"})
    svc = services(request)
    body = await json_body(request, optional=True)
    label = optional_str(body, "label") or ""
    ttl = optional_int(body, "ttl_seconds") or PAIRING_CODE_TTL_SECONDS
    ttl = max(30, min(ttl, PAIRING_CODE_MAX_TTL_SECONDS))
    code, expires_at = svc.tokens.create_pairing_code(label=label, ttl_seconds=ttl)
    return ok({
        "code": code,
        "expires_at": expires_at,
        "pair_url": f"{request.scheme}://{request.host}/api/v2/devices/pair",
    }, status=201)


async def pair(request: web.Request) -> web.Response:
    """Public endpoint: exchange a pairing code for a device token."""
    svc = services(request)
    body = await json_body(request)
    code = require_str(body, "code").strip()
    label = optional_str(body, "label") or ""
    locale = normalize_locale(optional_str(body, "locale"))
    issued = svc.tokens.redeem_pairing_code(code, label=label, locale=locale)
    payload: dict[str, object] = {
        "token": issued["token"],
        "expires_at": issued["expires_at"],
        "client": issued["client"],
    }
    push_token = optional_str(body, "push_token")
    platform_raw = body.get("platform")
    if push_token and platform_raw in PLATFORMS:
        device = svc.devices.register(
            client_id=issued["client"]["id"],
            platform=platform_raw,
            push_token=push_token,
            label=label,
            locale=locale,
        )
        payload["device"] = public_device(device)
    return ok(payload, status=201)


async def revoke_client(request: web.Request) -> web.Response:
    principal = principal_of(request)
    if not is_admin(principal):
        raise ApiError(403, "forbidden", "auth.missing_scope", {"scope": "admin"})
    svc = services(request)
    body = await json_body(request)
    client_id = require_str(body, "client_id")
    revoked = svc.tokens.revoke_client(client_id)
    devices = svc.devices.revoke_for_client(client_id)
    if not revoked and devices == 0:
        raise ApiError(404, "client_not_found")
    return ok({"revoked": revoked, "devices_revoked": devices, "client_id": client_id})


async def list_clients(request: web.Request) -> web.Response:
    principal = principal_of(request)
    if not is_admin(principal):
        raise ApiError(403, "forbidden", "auth.missing_scope", {"scope": "admin"})
    include_revoked = request.query.get("revoked") in ("1", "true")
    return ok({"clients": services(request).tokens.list_clients(include_revoked=include_revoked)})


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/devices", list_devices)
    router.add_post(f"{prefix}/devices", register_device)
    router.add_post(f"{prefix}/devices/pair", pair)
    router.add_post(f"{prefix}/devices/pairing-codes", create_pairing_code)
    router.add_post(f"{prefix}/devices/revoke-client", revoke_client)
    router.add_get(f"{prefix}/devices/clients", list_clients)
    router.add_delete(f"{prefix}/devices/{{id}}", delete_device)
