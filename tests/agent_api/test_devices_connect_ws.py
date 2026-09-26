"""Device pairing + push registration, connect/risk/permissions/control, and ``/ws/v2``."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient

from nanobot.agent_api.context import AgentApiServices
from nanobot.agent_api.push.base import LoggingPushProvider
from tests.agent_api.conftest import FakeAgent, auth

# ---------------------------------------------------------------------------
# devices
# ---------------------------------------------------------------------------


async def test_pairing_issues_device_token_and_registers_push(
    client: TestClient, services: AgentApiServices,
) -> None:
    minted = await client.post(
        "/api/v2/devices/pairing-codes", json={"label": "phone", "ttl_seconds": 120}, headers=auth(),
    )
    assert minted.status == 201
    code = (await minted.json())["code"]

    paired = await client.post(
        "/api/v2/devices/pair",
        json={"code": code, "platform": "android", "push_token": "fcm-1", "locale": "ar"},
    )
    assert paired.status == 201
    body = await paired.json()
    device_token = body["token"]
    assert body["client"]["kind"] == "device"
    assert "push" in body["client"]["scopes"]
    assert body["expires_at"] is None
    assert body["device"]["platform"] == "android"
    assert "push_token" not in body["device"]

    me = await (await client.get("/api/v2/me", headers=auth(device_token))).json()
    assert me["kind"] == "device" and me["locale"] == "ar" and me["dir"] == "rtl"

    reused = await client.post("/api/v2/devices/pair", json={"code": code})
    assert reused.status == 409
    unknown = await client.post("/api/v2/devices/pair", json={"code": "00000000"})
    assert unknown.status == 404

    registered = await client.post(
        "/api/v2/devices",
        json={"platform": "ios", "push_token": "apns-1", "label": "ipad"},
        headers=auth(device_token),
    )
    assert registered.status == 201
    mine = await (await client.get("/api/v2/devices", headers=auth(device_token))).json()
    assert {d["platform"] for d in mine["devices"]} == {"android", "ios"}

    other = services.tokens.issue("device", label="other")
    forbidden = await client.delete(
        f"/api/v2/devices/{registered_id(await registered.json())}", headers=auth(other["token"]),
    )
    assert forbidden.status == 403
    deleted = await client.delete(
        f"/api/v2/devices/{registered_id(await registered.json())}", headers=auth(device_token),
    )
    assert deleted.status == 200
    remaining = await (await client.get("/api/v2/devices", headers=auth(device_token))).json()
    assert [d["platform"] for d in remaining["devices"]] == ["android"]

    revoked = await client.post(
        "/api/v2/devices/revoke-client", json={"client_id": me["client_id"]}, headers=auth(),
    )
    assert (await revoked.json())["revoked"] is True
    assert (await client.get("/api/v2/me", headers=auth(device_token))).status == 401


def registered_id(body: dict[str, Any]) -> str:
    return str(body["id"])


async def test_pairing_code_requires_admin(client: TestClient, services: AgentApiServices) -> None:
    web = services.tokens.issue("web")
    resp = await client.post("/api/v2/devices/pairing-codes", headers=auth(web["token"]))
    assert resp.status == 403


async def test_push_router_skips_when_ws_connected_and_delivers_otherwise(
    client: TestClient, services: AgentApiServices,
) -> None:
    provider = LoggingPushProvider()
    services.push._providers = [provider]  # pyright: ignore[reportPrivateUsage]
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    services.devices.register(client_id="c", platform="android", push_token="t", label="", locale="en")

    services.approvals.open(
        type="generic", summary="s", session=session, run=None, expires_at=None, source_id="p1",
    )
    await services.push.wait_idle()
    assert [p["kind"] for _, p in provider.sent] == ["approval"]
    assert "approval_id" in provider.sent[0][1] and "price" not in json.dumps(provider.sent[0][1])

    ws = await client.ws_connect("/ws/v2", headers=auth())
    await ws.receive_json()  # hello
    services.approvals.open(
        type="generic", summary="s", session=session, run=None, expires_at=None, source_id="p2",
    )
    await services.push.wait_idle()
    assert len(provider.sent) == 1
    await ws.close()


# ---------------------------------------------------------------------------
# connect / control
# ---------------------------------------------------------------------------


async def test_connect_snapshot_and_risk_profile_update(client: TestClient) -> None:
    snapshot = await (await client.get("/api/v2/connect", headers=auth())).json()
    assert snapshot["brokers"]["oanda"]["configured"] is False
    assert snapshot["runtime_state"] == {"paused": False, "kill_switch": False, "paper_mode": True}
    assert snapshot["risk"]["profile"]["name"] == "balanced"
    assert snapshot["mt5_permissions"]["permissions"]["level"] == "propose"

    changed = await client.put(
        "/api/v2/connect/risk-profile", json={"name": "conservative"}, headers=auth(),
    )
    assert changed.status == 200
    body = await changed.json()
    assert body["profile"]["name"] == "conservative"
    assert body["values"]["risk_pct_default"] < 1.0

    bad = await client.put("/api/v2/connect/risk-profile", json={"name": "yolo"}, headers=auth())
    assert bad.status == 400
    assert (await bad.json())["error"]["code"] == "trading_risk_error"

    field = await client.put(
        "/api/v2/connect/risk/min_rr", json={"value": 2.5}, headers=auth(),
    )
    assert field.status == 200
    values = (await field.json())["values"]
    assert values["min_rr"] == 2.5
    assert values["risk_profile"] == "custom"


async def test_mt5_permissions_update_is_audited(client: TestClient) -> None:
    current = await (await client.get("/api/v2/connect/mt5/permissions", headers=auth())).json()
    assert current["permissions"]["level"] == "propose"

    updated = await client.put(
        "/api/v2/connect/mt5/permissions",
        json={"permissions": {"level": "execute", "can_open": True, "max_lot_per_order": 0.2}},
        headers=auth(),
    )
    assert updated.status == 200
    body = await updated.json()
    assert body["permissions"]["level"] == "execute"
    assert body["last_action"]["who"] == "service:bootstrap"
    assert body["audit"][0]["to_level"] == "execute"

    invalid = await client.put(
        "/api/v2/connect/mt5/permissions", json={"permissions": {"level": "god"}}, headers=auth(),
    )
    assert invalid.status == 400


async def test_control_endpoints_toggle_runtime_state(client: TestClient) -> None:
    killed = await (await client.post("/api/v2/control/kill", headers=auth())).json()
    assert killed["runtime_state"]["kill_switch"] is True
    paused = await (await client.post("/api/v2/control/pause", headers=auth())).json()
    assert paused["runtime_state"]["paused"] is True
    resumed = await (await client.post("/api/v2/control/resume", headers=auth())).json()
    assert resumed["runtime_state"]["paused"] is False
    restored = await (await client.post(
        "/api/v2/control/kill", json={"enabled": False}, headers=auth(),
    )).json()
    assert restored["runtime_state"]["kill_switch"] is False
    bad = await client.post("/api/v2/control/kill", json={"enabled": "yes"}, headers=auth())
    assert bad.status == 400


# ---------------------------------------------------------------------------
# websocket
# ---------------------------------------------------------------------------


async def _collect_until(ws: Any, predicate: Any, timeout: float = 3.0) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    async with asyncio.timeout(timeout):
        while True:
            msg = await ws.receive()
            assert msg.type == WSMsgType.TEXT, msg
            frame = json.loads(msg.data)
            frames.append(frame)
            if predicate(frame):
                return frames


async def test_ws_multiplex_send_and_stream(client: TestClient, agent: FakeAgent) -> None:
    ws = await client.ws_connect("/ws/v2?token=nbat_test-bootstrap-token")
    hello = await ws.receive_json()
    assert hello["type"] == "hello" and hello["client_id"] == "bootstrap"

    await ws.send_json({"op": "ping", "req": "p1"})
    pong = await ws.receive_json()
    assert pong["type"] == "pong" and pong["req"] == "p1"

    await ws.send_json({"op": "send", "session": "s-ws", "text": "hi", "req": "r1"})
    frames = await _collect_until(ws, lambda f: f.get("type") == "event" and f["event"]["kind"] == "end")
    ack = next(f for f in frames if f["type"] == "ack")
    assert ack["op"] == "send" and ack["req"] == "r1" and ack["run_id"].startswith("r_")
    kinds = [f["event"]["kind"] for f in frames if f["type"] == "event"]
    assert kinds[0] == "state" and "delta" in kinds and kinds[-1] == "end"
    assert all(f["event"]["session"] == "s-ws" for f in frames if f["type"] == "event")

    await ws.send_json({"op": "subscribe", "session": "s-ws", "after": frames[1]["event"]["id"]})
    replay = await _collect_until(ws, lambda f: f.get("type") == "ack")
    assert replay[-1]["replayed"] >= 1
    assert replay[-1]["state"]["state"] == "completed"

    await ws.send_json({"op": "dance"})
    err = await ws.receive_json()
    assert err["type"] == "error" and err["error"]["code"] == "unknown_op"

    await ws.send_str("not json")
    err = await ws.receive_json()
    assert err["error"]["code"] == "invalid_json"

    await ws.send_json({"op": "unsubscribe", "session": "s-ws"})
    ack = await ws.receive_json()
    assert ack["removed"] is True
    await ws.close()


async def test_ws_requires_token_and_scopes(client: TestClient, services: AgentApiServices) -> None:
    denied = await client.get("/ws/v2")
    assert denied.status == 401

    readonly = services.tokens.issue("service", scopes=["read"])
    ws = await client.ws_connect(f"/ws/v2?token={readonly['token']}")
    await ws.receive_json()
    await ws.send_json({"op": "send", "session": "s", "text": "hi", "req": "x"})
    err = await ws.receive_json()
    assert err["type"] == "error" and err["error"]["code"] == "forbidden" and err["req"] == "x"
    await ws.close()


async def test_ws_cancel_and_approve(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    agent.block = asyncio.Event()
    ws = await client.ws_connect("/ws/v2", headers=auth())
    await ws.receive_json()
    await ws.send_json({"op": "send", "session": "s-cancel", "text": "hi"})
    await _collect_until(ws, lambda f: f.get("type") == "ack")
    await ws.send_json({"op": "cancel", "session": "s-cancel"})
    # The run's ``end`` event is published while ``cancel`` awaits the task, so it
    # precedes the ack on the wire.
    frames = await _collect_until(ws, lambda f: f.get("type") == "ack" and f["op"] == "cancel")
    assert frames[-1]["cancelled"] is True
    ends = [f for f in frames if f["type"] == "event" and f["event"]["kind"] == "end"]
    assert ends and ends[-1]["event"]["data"]["outcome"] == "cancelled"

    record = services.approvals.open(
        type="generic", summary="s", session="s-cancel", run=None, expires_at=None, source_id="p9",
    )
    await _collect_until(ws, lambda f: f.get("type") == "event" and f["event"]["kind"] == "approval")
    await ws.send_json({"op": "approve", "approval_id": record["id"], "decision": "cancel"})
    frames = await _collect_until(ws, lambda f: f.get("type") == "ack" and f["op"] == "approve")
    assert frames[-1]["approval"]["status"] == "cancelled"
    await ws.close()
