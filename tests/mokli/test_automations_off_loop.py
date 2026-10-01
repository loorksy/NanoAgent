"""The automation list must not block the event loop on session files."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from websockets.datastructures import Headers
from websockets.http11 import Request

from mokli.channels.websocket.runtime import WebSocketChannel, WebSocketConfig
from mokli.surface.gateway_services import build_gateway_services


def _channel(bus: Any, workspace: Path) -> WebSocketChannel:
    cfg: dict[str, Any] = {
        "enabled": True,
        "allowFrom": ["*"],
        "host": "127.0.0.1",
        "port": 29878,
        "path": "/ws",
        "websocketRequiresToken": False,
    }
    parsed = WebSocketConfig.model_validate(cfg)
    gateway = build_gateway_services(
        config=parsed,
        bus=bus,
        session_manager=None,
        static_dist_path=None,
        workspace_path=workspace,
        default_restrict_to_workspace=False,
        runtime_model_name=None,
        runtime_surface="browser",
        runtime_capabilities_overrides=None,
    )
    return WebSocketChannel(cfg, bus, gateway=gateway)


async def test_automation_list_leaves_the_event_loop_free(
    tmp_path: Path,
    monkeypatch,
) -> None:
    order: list[str] = []

    def slow(*_args: object, **_kwargs: object) -> dict[str, list[object]]:
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        return {"jobs": [{"id": "listed-off-loop"}]}

    monkeypatch.setattr("mokli.surface.ws_http.all_automations_payload", slow)
    channel = _channel(MagicMock(), tmp_path)
    channel.gateway.tokens.api_tokens["tok"] = time.monotonic() + 300.0
    request = Request("/api/mokli/automations", Headers([("Authorization", "Bearer tok")]))

    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    response = await channel.gateway.http._dispatch_automation_routes(
        request,
        "/api/mokli/automations",
    )
    await pending
    assert order[0] == "tick"
    assert "main" not in order
    assert order.count("worker") == 1
    assert time.perf_counter() - started < 0.35
    body = json.loads(response.body.decode())
    assert body["jobs"][0]["id"] == "listed-off-loop"
