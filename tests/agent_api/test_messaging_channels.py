"""Telegram token and WhatsApp QR on the connect page."""

from __future__ import annotations

import json

from aiohttp.test_utils import TestClient

from agent_api.conftest import auth
from mokli.agent_api.context import AgentApiServices


async def test_connect_channels_lists_telegram_and_whatsapp(client: TestClient) -> None:
    response = await client.get("/api/v2/connect/channels", headers=auth())
    assert response.status == 200
    body = await response.json()
    names = [row["name"] for row in body["channels"]]
    assert names == ["telegram", "whatsapp"]
    assert "token" not in json.dumps(body)


async def test_telegram_token_is_saved_and_not_echoed(
    client: TestClient,
    services: AgentApiServices,
) -> None:
    secret = "123456:telegram-secret"
    response = await client.post(
        "/api/v2/connect/channels/telegram",
        json={"token": secret},
        headers=auth(),
    )
    assert response.status == 200
    body = await response.json()
    assert body["name"] == "telegram"
    assert body["saved"] is True
    assert secret not in json.dumps(body)
    stored = json.loads(services.config_path.read_text(encoding="utf-8"))
    assert stored["channels"]["telegram"]["token"] == secret
    assert stored["channels"]["telegram"]["enabled"] is True

    missing = await client.post(
        "/api/v2/connect/channels/telegram",
        json={"token": "  "},
        headers=auth(),
    )
    assert missing.status == 400


async def test_whatsapp_qr_is_a_data_url(client: TestClient, monkeypatch) -> None:
    class FakeConnect:
        async def handle(self, action: str, query: dict) -> dict:
            assert action == "start"
            return {
                "session_id": "sess-1",
                "status": "pending",
                "qr_url": "mokli-whatsapp-pairing",
                "interval_ms": 2000,
                "message": "Waiting for the WhatsApp scan.",
            }

    monkeypatch.setattr(
        "mokli.agent_api.messaging._connectors",
        {"whatsapp": FakeConnect()},
    )
    response = await client.post(
        "/api/v2/connect/channels/whatsapp",
        json={"action": "start"},
        headers=auth(),
    )
    assert response.status == 200
    body = await response.json()
    assert body["session_id"] == "sess-1"
    assert body["status"] == "pending"
    assert body["qr_data_url"].startswith("data:image/png;base64,")
    assert body["message"] == "Waiting for the WhatsApp scan."
    assert "mokli-whatsapp-pairing" not in json.dumps(body)


async def test_pairing_code_can_be_entered(client: TestClient, monkeypatch, tmp_path) -> None:
    from mokli.pairing import store

    monkeypatch.setattr(store, "_store_path", lambda: tmp_path / "pairing.json")
    code = store.generate_code("telegram", "123")
    listed = await client.get("/api/v2/connect/pairing", headers=auth())
    assert listed.status == 200
    pending = (await listed.json())["pending"]
    assert pending[0]["code"] == code
    assert pending[0]["channel"] == "telegram"
    assert "123" not in json.dumps(pending)

    approved = await client.post(
        "/api/v2/connect/pairing",
        json={"code": code.replace("-", ""), "locale": "ar"},
        headers=auth(),
    )
    assert approved.status == 200
    body = await approved.json()
    assert body["ok"] is True
    assert body["channel"] == "telegram"
    assert "123" not in json.dumps(body)

    missing = await client.post(
        "/api/v2/connect/pairing",
        json={"code": "ZZZZ-ZZZZ", "locale": "ar"},
        headers=auth(),
    )
    assert missing.status == 404
    error = await missing.json()
    assert "الرمز" in error["error"]["details"]["message"]
