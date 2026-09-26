"""FCM v1 provider: key-only ``data`` plus a catalog-localized ``notification`` block."""

from __future__ import annotations

import json
from typing import Any

import httpx

from nanobot.agent_api.devices import DeviceRecord
from nanobot.agent_api.push.base import PushPayload
from nanobot.agent_api.push.fcm import ANDROID_CHANNEL_ID, FcmV1Provider, localized_notification
from nanobot.agent_api.push.router import payload_for


def _device(locale: str) -> DeviceRecord:
    return {
        "id": "dev1",
        "client_id": "c1",
        "platform": "android",
        "push_token": "fcm-token",
        "label": "pixel",
        "locale": locale,
        "created_at": 0,
        "updated_at": 0,
        "revoked": False,
    }


def _approval_payload() -> PushPayload:
    event: Any = {
        "id": "01A",
        "session": "s1",
        "run": "r1",
        "ts": 1,
        "kind": "approval",
        "data": {"approval_id": "a1", "type": "execution", "status": "pending"},
    }
    payload = payload_for(event)
    assert payload is not None
    return payload


def test_localized_notification_uses_device_locale() -> None:
    payload = _approval_payload()
    ar = localized_notification(payload, "ar")
    en = localized_notification(payload, "en")
    assert ar["title"] == "مطلوب تأكيد"
    assert en["title"] == "Confirmation required"
    assert en["body"] and ar["body"] != en["body"]
    # Unknown locale falls back to English rather than leaking the raw key.
    assert localized_notification(payload, "xx")["title"] == en["title"]


async def test_fcm_message_carries_data_and_localized_notification() -> None:
    seen: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer oauth-token"
        return httpx.Response(200, json={"name": "projects/p/messages/1"})

    async def token() -> str:
        return "oauth-token"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = FcmV1Provider("proj-1", token, client=client)
        assert provider.endpoint.endswith("/projects/proj-1/messages:send")
        ok = await provider.send(_device("ar"), _approval_payload())

    assert ok is True
    message = seen[0]["message"]
    assert message["token"] == "fcm-token"
    assert message["notification"] == {
        "title": "مطلوب تأكيد",
        "body": "اقترح الوكيل إجراءً يحتاج قرارك.",
    }
    assert message["android"]["priority"] == "high"
    assert message["android"]["notification"]["channel_id"] == ANDROID_CHANNEL_ID
    data = message["data"]
    assert data["kind"] == "approval"
    assert data["approval_id"] == "a1"
    assert data["deep_link"] == "nanoagent://approvals/a1"
    assert json.loads(data["args"]) == {"type": "execution"}
    # FCM data values must all be strings and never contain prices/levels.
    assert all(isinstance(value, str) for value in data.values())
    assert not any(key in data for key in ("price", "entry", "stop", "targets"))
