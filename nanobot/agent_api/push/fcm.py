"""FCM HTTP v1 provider (Android). Access tokens are supplied by the caller."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import httpx
from loguru import logger

from nanobot.agent_api.devices import DeviceRecord
from nanobot.agent_api.labels import Labels
from nanobot.agent_api.push.base import PushPayload
from nanobot.security.network import validate_url_target

FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
ANDROID_CHANNEL_ID = "default"
AccessTokenProvider = Callable[[], Awaitable[str]]


class FcmV1Provider:
    """Send key-only ``data`` plus a ``notification`` block localized to the device locale.

    The notification text comes from the label catalog (never prices or levels), so the
    system tray can show it while the app is in the background; the app re-resolves the
    keys from ``data`` when the user opens it.
    """

    name = "fcm"

    def __init__(
        self,
        project_id: str,
        access_token: AccessTokenProvider,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._project_id = project_id
        self._access_token = access_token
        self._client = client
        self._timeout = timeout

    @property
    def endpoint(self) -> str:
        return FCM_ENDPOINT.format(project=self._project_id)

    def supports(self, device: DeviceRecord) -> bool:
        return device["platform"] == "android"

    async def send(self, device: DeviceRecord, payload: PushPayload) -> bool:
        url = self.endpoint
        ok, error = validate_url_target(url)
        if not ok:
            logger.warning("agent_api fcm endpoint rejected: {}", error)
            return False
        data = {key: json.dumps(value) if not isinstance(value, str) else value
                for key, value in _flatten(payload).items()}
        body = {
            "message": {
                "token": device["push_token"],
                "data": data,
                "notification": localized_notification(payload, device["locale"]),
                "android": {
                    "priority": "high",
                    "notification": {"channel_id": ANDROID_CHANNEL_ID},
                },
            }
        }
        headers = {
            "Authorization": f"Bearer {await self._access_token()}",
            "Content-Type": "application/json; UTF-8",
        }
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("agent_api fcm send failed: {}", exc)
            return False
        finally:
            if owns_client:
                await client.aclose()
        if response.status_code >= 400:
            logger.warning("agent_api fcm send rejected: {} {}", response.status_code, response.text[:200])
            return False
        return True


def _flatten(payload: PushPayload) -> dict[str, object]:
    out: dict[str, object] = {
        "kind": payload["kind"],
        "title_key": payload["title_key"],
        "body_key": payload["body_key"],
        "args": payload["args"],
        "deep_link": payload["deep_link"],
    }
    if payload["session"] is not None:
        out["session"] = payload["session"]
    if payload["approval_id"] is not None:
        out["approval_id"] = payload["approval_id"]
    return out


def localized_notification(payload: PushPayload, locale: str | None) -> dict[str, str]:
    """Resolve ``title_key`` / ``body_key`` through the catalog for the device locale."""
    labels = Labels(locale)
    return {"title": labels(payload["title_key"]), "body": labels(payload["body_key"])}
